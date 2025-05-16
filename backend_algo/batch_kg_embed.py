import sys
import time
import requests
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict
from sqlalchemy.orm import Session
from pathlib import Path
import re

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from backend.database import SessionLocal
from backend import models

# 初始化ChromaDB HTTP client
chroma_client = chromadb.HttpClient(host='localhost', port=8002)
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="API_KEY_IS_NOT_NEEDED",
    api_base="http://10.176.64.152:11435/v1",
    model_name="bge-m3"
)
kg_collection = chroma_client.get_or_create_collection(
    name="kg_triples",
    embedding_function=openai_ef
)

# 简单三元组抽取规则（可升级为LLM抽取）
def extract_triples(paper: models.Paper) -> List[Dict]:
    triples = []
    # 1. 从标题抽取（如"A improves B"）
    title = paper.title or ""
    m = re.match(r"(.+?) (improves|improving|for|enables|applies to|applied to|based on|using|with|in|via) (.+)", title, re.I)
    if m:
        triples.append({
            "head": m.group(1).strip(),
            "relation": m.group(2).strip(),
            "tail": m.group(3).strip(),
            "source": title
        })
    # 2. 从关键词生成简单关系
    if paper.keywords:
        for kw in paper.keywords:
            triples.append({
                "head": paper.title,
                "relation": "has_keyword",
                "tail": kw,
                "source": f"title-keyword: {kw}"
            })
    # 3. 从摘要抽取（如"X is a method for Y"）
    abstract = paper.abstract or ""
    m2 = re.match(r"(.+?) is a (method|model|approach|algorithm) for (.+?)\. ", abstract, re.I)
    if m2:
        triples.append({
            "head": m2.group(1).strip(),
            "relation": f"is_a_{m2.group(2).strip()}_for",
            "tail": m2.group(3).strip(),
            "source": abstract
        })
    # 可扩展更多规则
    return triples

def get_unprocessed_papers(db: Session, limit: int = 100) -> List[models.Paper]:
    # 只处理已入库但未做KG处理的论文
    return db.query(models.Paper).filter(
        models.Paper.is_processed == True,
        getattr(models.Paper, 'is_kg_processed', False) == False
    ).limit(limit).all()

def process_paper_kg(db: Session, paper: models.Paper) -> int:
    triples = extract_triples(paper)
    success = 0
    for idx, triple in enumerate(triples):
        try:
            triple_text = f"{triple['head']} [REL] {triple['relation']} [TAIL] {triple['tail']}"
            unique_id = f"{paper.id}_{idx}"
            kg_collection.add(
                ids=[unique_id],
                documents=[triple_text],
                metadatas=[{
                    "head": triple['head'],
                    "relation": triple['relation'],
                    "tail": triple['tail'],
                    "paper_id": paper.id,
                    "source": triple['source']
                }]
            )
            success += 1
        except Exception as e:
            print(f"Failed to add triple for paper {paper.id}: {e}")
    # 处理完毕后，标记为已处理
    try:
        paper.is_kg_processed = True
        db.commit()
    except Exception as e:
        print(f"Failed to update is_kg_processed for paper {paper.id}: {e}")
        db.rollback()
    return success

def batch_process_kg(batch_size: int = 10):
    db = SessionLocal()
    try:
        while True:
            papers = get_unprocessed_papers(db, batch_size)
            if not papers:
                print("All papers processed for KG!")
                break
            print(f"Processing {len(papers)} papers for KG...")
            total_triples = 0
            for paper in papers:
                cnt = process_paper_kg(db, paper)
                total_triples += cnt
            print(f"Processed {total_triples} triples from {len(papers)} papers.")
            time.sleep(1)
    finally:
        try:
            total_kg = kg_collection.count()
            print(f"\nTotal triples in kg_triples: {total_kg}")
        except Exception as e:
            print(f"\nError getting KG triple count: {str(e)}")
        db.close()

if __name__ == "__main__":
    batch_process_kg()
