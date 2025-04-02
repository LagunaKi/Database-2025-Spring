import requests
import time
from typing import List, Dict, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

from pydantic import BaseModel

# Configuration
BACKEND_URL = "http://localhost:8000"  # backend API地址
ALGO_URL = "http://localhost:8001"  # backend_algo API地址
ARXIV_API_URL = "http://export.arxiv.org/api/query"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


class PaperData(BaseModel):
    """论文数据模型"""
    title: str
    authors: List[str]
    abstract: str
    keywords: List[str]
    published_date: Optional[str] = None
    pdf_url: str


def fetch_papers_from_arxiv(search_query: str, max_results: int = 10) -> List[PaperData]:
    """从arXiv API获取论文数据"""
    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    
    try:
        response = requests.get(ARXIV_API_URL, params=params)
        response.raise_for_status()
        
        # 解析Atom格式的响应
        root = ET.fromstring(response.content)
        papers = []
        
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            # 提取标题
            title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
            
            # 提取作者
            authors = [
                author.find("{http://www.w3.org/2005/Atom}name").text
                for author in entry.findall("{http://www.w3.org/2005/Atom}author")
            ]
            
            # 提取摘要
            abstract = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip()
            
            # 提取发表日期
            published = entry.find("{http://www.w3.org/2005/Atom}published").text
            published_date = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
            
            # 提取PDF链接
            pdf_url = None
            for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib["href"]
                    break
            
            if not pdf_url:
                continue  # 跳过没有PDF的论文
                
            # 构造论文数据
            papers.append(PaperData(
                title=title,
                authors=authors,
                abstract=abstract,
                keywords=[],  # arXiv不提供关键词，可以留空或从标题/摘要提取
                published_date=published_date,
                pdf_url=pdf_url
            ))
            
        return papers
        
    except Exception as e:
        print(f"从arXiv获取论文数据失败: {e}")
        return []


def create_backend_paper(paper: PaperData) -> Optional[int]:
    """在backend创建论文记录"""
    url = f"{BACKEND_URL}/api/papers/"
    payload = {
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "keywords": paper.keywords,
        "pdf_url": paper.pdf_url,
        "published_date": paper.published_date
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()["id"]
        except Exception as e:
            print(f"创建论文记录失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
            time.sleep(RETRY_DELAY)
    
    return None


def embed_paper_content(paper_id: int, paper: PaperData) -> bool:
    """在backend_algo嵌入论文内容"""
    url = f"{ALGO_URL}/papers/embed"
    payload = {
        "paper_id": paper_id,
        "title": paper.title,
        "abstract": paper.abstract,
        "keywords": paper.keywords
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"嵌入论文内容失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
            time.sleep(RETRY_DELAY)
    
    return False


def update_paper_status(paper_id: int) -> bool:
    """更新论文处理状态"""
    url = f"{BACKEND_URL}/api/papers/{paper_id}"
    payload = {"is_processed": True}
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.patch(url, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"更新论文状态失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
            time.sleep(RETRY_DELAY)
    
    return False


def main(search_query: str, max_papers: int = 10):
    """主处理函数"""
    print(f"从arXiv搜索论文: {search_query}")
    
    # 从arXiv获取论文数据
    papers = fetch_papers_from_arxiv(search_query, max_papers)
    if not papers:
        print("没有找到符合条件的论文")
        return
    
    print(f"找到 {len(papers)} 篇论文")
    
    success_count = 0
    for i, paper in enumerate(papers, 1):
        print(f"\n处理论文 {i}/{len(papers)}: {paper.title[:50]}...")
        
        # 步骤1: 在backend创建论文记录
        paper_id = create_backend_paper(paper)
        if not paper_id:
            print("→ 跳过，无法创建论文记录")
            continue
        
        # 步骤2: 在backend_algo嵌入论文内容
        if not embed_paper_content(paper_id, paper):
            print("→ 跳过，无法嵌入论文内容")
            continue
        
        # 步骤3: 更新论文处理状态
        if not update_paper_status(paper_id):
            print("→ 警告: 论文内容已嵌入但状态更新失败")
        else:
            success_count += 1
            print("→ 处理完成")
    
    print(f"\n处理完成! 成功导入 {success_count}/{len(papers)} 篇论文")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="论文数据加载工具 (arXiv API)")
    parser.add_argument("search_query", help="arXiv搜索查询语句，例如: 'cat:cs.CV'")
    parser.add_argument("--max_papers", type=int, default=10, 
                       help="最大获取论文数量 (默认: 10)")
    args = parser.parse_args()
    
    main(args.search_query, args.max_papers)
