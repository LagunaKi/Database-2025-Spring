import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List
import time
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from backend.database import SessionLocal
from backend import models, crud

ARXIV_API_URL = "http://export.arxiv.org/api/query"

class ArxivPaper:
    def __init__(self, entry):
        # Required fields with error handling
        self.id = entry.find("{http://www.w3.org/2005/Atom}id").text.split('/')[-1]
        
        title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
        self.title = title_elem.text.strip() if title_elem is not None else "No title"
        
        # Authors (list)
        self.authors = []
        for author in entry.findall("{http://www.w3.org/2005/Atom}author"):
            name = author.find("{http://www.w3.org/2005/Atom}name")
            if name is not None and name.text:
                self.authors.append(name.text)
        
        # Abstract (optional)
        summary_elem = entry.find("{http://www.w3.org/2005/Atom}summary")
        self.abstract = summary_elem.text.strip() if summary_elem is not None else "No abstract"
        
        # Keywords (from arXiv categories)
        categories = entry.findall("{http://www.w3.org/2005/Atom}category")
        self.keywords = [cat.attrib["term"] for cat in categories] if categories else []
        
        # Published date
        published_elem = entry.find("{http://www.w3.org/2005/Atom}published")
        self.published = published_elem.text if published_elem is not None else None
        self.pdf_url = next(
            (link.attrib["href"] for link in entry.findall("{http://www.w3.org/2005/Atom}link") 
             if link.attrib.get("title") == "pdf"),
            None
        )

def fetch_papers_from_arxiv(search_query: str, max_results: int = 10, start: int = 0) -> List[ArxivPaper]:
    params = {
        "search_query": search_query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    
    response = requests.get(ARXIV_API_URL, params=params)
    response.raise_for_status()
    
    root = ET.fromstring(response.content)
    return [ArxivPaper(entry) for entry in root.findall("{http://www.w3.org/2005/Atom}entry")]

def save_papers_to_db(papers: List[ArxivPaper]):
    db = SessionLocal()
    try:
        for paper in papers:
            if not crud.get_paper(db, paper_id=paper.id): # 只有当论文不存在时才会添加到数据库
                db_paper = models.Paper(
                    id=paper.id,
                    title=paper.title,
                    authors=paper.authors,
                    abstract=paper.abstract,
                    keywords=paper.keywords,
                    published_date=datetime.strptime(paper.published, "%Y-%m-%dT%H:%M:%SZ"),
                    pdf_url=paper.pdf_url
                )
                db.add(db_paper)
        db.commit()
    finally:
        db.close()

def sync_arxiv_papers():
    categories = ["cs.CL", "cs.AI", "cs.LG"]  # NLP, AI, ML categories
    for category in categories:
        all_papers = []
        # Fetch 1000 papers in batches of 100
        for start in range(0, 1000, 100):
            papers = fetch_papers_from_arxiv(
                f"cat:{category}", 
                max_results=100,
                start=start
            )
            all_papers.extend(papers)
            time.sleep(5)  # Increased delay to be more polite
            
        save_papers_to_db(all_papers)

if __name__ == "__main__":
    sync_arxiv_papers()
