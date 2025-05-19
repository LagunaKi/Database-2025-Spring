import sys
import time
import argparse
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict
from sqlalchemy.orm import Session
from pathlib import Path
import re

# 新增依赖
import spacy
import scispacy
from spacy.tokens import Doc

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

# 加载SciSpacy模型
try:
    nlp = spacy.load("en_core_sci_lg")
except Exception as e:
    print("请先安装en_core_sci_lg模型: python -m spacy download en_core_sci_lg")
    raise e

# 实体类型映射
ENTITY_TYPES = {
    "METHOD": ["METHOD", "MODEL", "ALGORITHM", "APPROACH"],
    "TASK": ["TASK", "PROBLEM", "APPLICATION"],
    "DATASET": ["DATASET"],
    "METRIC": ["METRIC", "PERFORMANCE", "ACCURACY", "F1", "SCORE", "PRECISION", "RECALL"]
}

# 规则抽取定义、性能、适用任务等
DEF_PATTERNS = [
    re.compile(r"([A-Za-z0-9\- ]+) (is|are|refers to|means|stands for) (an? .{10,200}?)[\.;]", re.I),
    re.compile(r"([A-Za-z0-9\- ]+), (an? .{10,200}?)[\.;]", re.I)
]
PERF_PATTERNS = [
    re.compile(r"([A-Za-z0-9\- ]+) (achieves|obtains|reaches|yields|attains|reports) (\d{2,3}\.?\d*)%? (accuracy|f1|score|precision|recall)[\s\w]*on ([A-Za-z0-9\- ]+)", re.I),
    re.compile(r"(accuracy|f1|score|precision|recall) of ([A-Za-z0-9\- ]+) (is|was|reaches|achieves) (\d{2,3}\.?\d*)%? on ([A-Za-z0-9\- ]+)", re.I)
]
TASK_PATTERNS = [
    re.compile(r"([A-Za-z0-9\- ]+) (is|are|was|were|can be|could be|is used for|is suitable for|is applied to) ([A-Za-z0-9\- ]+ task|problem|application)", re.I)
]

# 用SciSpacy和规则抽取三元组

def extract_triples(paper: models.Paper) -> List[Dict]:
    triples = []
    text = (paper.title or "") + ". " + (paper.abstract or "")
    doc: Doc = nlp(text)
    # 1. 实体识别
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    # 2. 定义抽取
    for pat in DEF_PATTERNS:
        for m in pat.finditer(text):
            triples.append({
                "head": m.group(1).strip(),
                "relation": "has_definition",
                "tail": m.group(3 if pat.groups >= 3 else 2).strip(),
                "source": m.group(0),
                "paper_id": paper.id
            })
    # 3. 性能抽取
    for pat in PERF_PATTERNS:
        for m in pat.finditer(text):
            if pat.groups == 5:
                triples.append({
                    "head": m.group(1).strip(),
                    "relation": "achieves_accuracy",
                    "tail": f"{m.group(3)}% {m.group(4)} on {m.group(5)}",
                    "source": m.group(0),
                    "paper_id": paper.id
                })
            else:
                triples.append({
                    "head": m.group(2).strip(),
                    "relation": "achieves_accuracy",
                    "tail": f"{m.group(4)}% {m.group(1)} on {m.group(5)}",
                    "source": m.group(0),
                    "paper_id": paper.id
                })
    # 4. 适用任务抽取
    for pat in TASK_PATTERNS:
        for m in pat.finditer(text):
            triples.append({
                "head": m.group(1).strip(),
                "relation": "suitable_for_task",
                "tail": m.group(3).strip(),
                "source": m.group(0),
                "paper_id": paper.id
            })
    # 5. 论文提出方法
    for ent, label in entities:
        if label in ENTITY_TYPES["METHOD"]:
            triples.append({
                "head": ent,
                "relation": "proposed_in",
                "tail": paper.id,
                "source": paper.title,
                "paper_id": paper.id
            })
    # 6. 关键词
    if paper.keywords:
        for kw in paper.keywords:
            triples.append({
                "head": paper.title,
                "relation": "has_keyword",
                "tail": kw,
                "source": f"title-keyword: {kw}",
                "paper_id": paper.id
            })
    return triples

def get_unprocessed_papers(db: Session, limit: int = 100) -> List[models.Paper]:
    return db.query(models.Paper).filter(
        models.Paper.is_processed == True,
        models.Paper.is_kg_processed == False
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
                    "paper_id": triple['paper_id'],
                    "source": triple['source']
                }]
            )
            success += 1
        except Exception as e:
            print(f"Failed to add triple for paper {paper.id}: {e}")
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

def reset_kg():
    # 清空kg_triples向量库
    kg_collection.delete(where={})
    # MySQL所有论文is_kg_processed=0
    db = SessionLocal()
    try:
        db.query(models.Paper).update({models.Paper.is_kg_processed: False})
        db.commit()
        print("Reset all is_kg_processed to 0.")
    except Exception as e:
        print(f"Failed to reset is_kg_processed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='重置KG向量库并重置MySQL is_kg_processed')
    args = parser.parse_args()
    if args.reset:
        reset_kg()
    batch_process_kg()
