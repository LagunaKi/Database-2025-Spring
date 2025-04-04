import sys
import time
import requests
import chromadb
from chromadb.utils import embedding_functions
from typing import List
from sqlalchemy.orm import Session
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from backend.database import SessionLocal
from backend import models, schemas

# Initialize ChromaDB HTTP client
chroma_client = chromadb.HttpClient(host='localhost', port=8002)
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="API_KEY_IS_NOT_NEEDED",
    api_base="http://10.176.64.152:11435/v1",
    model_name="bge-m3"
)
papers_collection = chroma_client.get_or_create_collection(
    name="papers",
    embedding_function=openai_ef
)

# 测试API连接
try:
    test_response = requests.post(
        "http://10.176.64.152:11435/v1/embeddings",
        json={"model": "bge-m3", "input": ["test connection"]},
        timeout=5
    )
    print(f"API connection test: {test_response.status_code}")
except Exception as e:
    print(f"API connection failed: {str(e)}")
    raise

def get_unprocessed_papers(db: Session, limit: int = 100) -> List[models.Paper]:
    return db.query(models.Paper).filter(
        models.Paper.is_processed == False
    ).limit(limit).all()

def process_paper(db: Session, paper: models.Paper) -> bool:
    try:
        print(f"Processing paper {paper.id}: {paper.title[:50]}...")
        
        # Prepare paper data
        combined_text = f"Title: {paper.title}\nAbstract: {paper.abstract}\nKeywords: {', '.join(paper.keywords) if paper.keywords else ''}"
        
        # Store in vector database
        print("Adding to ChromaDB collection...")
        papers_collection.add(
            ids=[str(paper.id)],
            documents=[combined_text],
            metadatas=[{
                "title": paper.title,
                "paper_id": paper.id,
                "processed": True
            }]
        )
        print("Successfully added to ChromaDB")
        
        # Update paper status
        paper.is_processed = True
        db.commit()
        print("Database status updated")
        return True
        
    except Exception as e:
        print(f"Failed to process paper {paper.id}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        print(f"Paper content: {combined_text[:200]}...")
        db.rollback()
        return False

def batch_process_papers(batch_size: int = 10):
    db = SessionLocal()
    try:
        while True:
            papers = get_unprocessed_papers(db, batch_size)
            if not papers:
                print("All papers processed!")
                break
                
            print(f"Processing {len(papers)} papers...")
            success = 0
            for paper in papers:
                if process_paper(db, paper):
                    success += 1
            
            print(f"Processed {success}/{len(papers)} papers successfully")
            time.sleep(1)  # Avoid rate limiting
            
    finally:
        # 输出chromadb中的论文总数
        try:
            total_papers = papers_collection.count()
            print(f"\nTotal papers in chromadb: {total_papers}")
        except Exception as e:
            print(f"\nError getting paper count: {str(e)}")
        db.close()

if __name__ == "__main__":
    batch_process_papers()
