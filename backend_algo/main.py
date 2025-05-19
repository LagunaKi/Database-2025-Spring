from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from backend_algo import schemas
import requests
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import time
from fastapi.middleware.cors import CORSMiddleware
import os
os.environ.pop("SSL_CERT_FILE", None)
from backend.database import SessionLocal
from backend import models
import numpy as np
import re

app = FastAPI()

# Initialize ChromaDB client with persistent mode
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
print("Successfully connected to ChromaDB HttpClient and papers collection with embedding_function")


URL = 'http://10.176.64.152:11434/v1'
MODEL = 'qwen2.5:7b'

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 只允许前端开发地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat/stream/")
async def chat_stream(conversation: schemas.Conversation):

    def generator():
        # Add prompt prefix to user messages
        processed_messages = []
        for msg in conversation.messages:
            if msg.role == 'user':
                processed_msg = msg.model_dump()
                processed_msg['content'] = f"你是一个论文搜索系统的ai工具，下面是对你的提问：{msg.content}"
                processed_messages.append(processed_msg)
            else:
                processed_messages.append(msg.model_dump())
                
        with requests.post(f'{URL}/chat/completions', json={
            'model': MODEL,
            'stream': True,
            'messages': processed_messages,
        }, stream=True, timeout=60) as resp:
            for raw_line in resp.iter_lines():
                line = raw_line.decode('utf-8').strip()
                if line == '':
                    continue
                if line.startswith('data: '):
                    line = line[len('data: '):]
                    if line == '[DONE]':
                        yield raw_line + b'\n'
                        break
                else:
                    yield raw_line + b'\n'
                    break
                # print(json.loads(line))
                yield raw_line + b'\n'
    
    return StreamingResponse(generator())


def get_papers_by_ids(paper_ids):
    db = SessionLocal()
    try:
        papers = db.query(models.Paper).filter(models.Paper.id.in_(paper_ids)).all()
        paper_dict = {paper.id: paper for paper in papers}
        return paper_dict
    finally:
        db.close()

@app.post("/chat/with-kg")
async def chat_with_kg(conversation: schemas.Conversation):
    # 1. 先用LLM生成初步理解
    processed_messages = []
    for msg in conversation.messages:
        if msg.role == 'user':
            processed_msg = msg.model_dump()
            processed_msg['content'] = f"你是一个论文搜索系统的ai工具，下面是对你的提问：{msg.content}"
            processed_messages.append(processed_msg)
        else:
            processed_messages.append(msg.model_dump())
    resp = requests.post(f'{URL}/chat/completions', json={
        'model': MODEL,
        'stream': False,
        'messages': processed_messages,
    }, stream=False, timeout=60)
    llm_answer = resp.json()['choices'][0]['message']['content']

    # 2. 用LLM理解结果分别在papers和kg_triples中检索
    papers_results = papers_collection.query(
        query_texts=[llm_answer],
        n_results=5,
        include=["documents", "metadatas", "distances"]
    )
    kg_collection = chroma_client.get_or_create_collection(
        name="kg_triples",
        embedding_function=openai_ef
    )
    kg_results = kg_collection.query(
        query_texts=[llm_answer],
        n_results=12, # 知识图谱检索数量
        include=["documents", "metadatas", "distances"]
    )

    # 通过paper_id批量查SQL数据库获取完整论文信息
    paper_ids = [meta.get("paper_id", "") for meta in papers_results['metadatas'][0]] if papers_results['metadatas'] else []
    paper_dict = get_papers_by_ids(paper_ids)
    papers = [
        {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "pdf_url": paper.pdf_url,
            "keywords": paper.keywords,
            "published_date": paper.published_date,
            "year": paper.published_date.year if paper.published_date else None
        }
        for pid in paper_ids if (paper := paper_dict.get(pid))
    ]

    # 3. 整合论文摘要、标题、知识图谱三元组，拼接为prompt
    context = "\n".join([
        f"论文: {meta['title']}\n摘要: {doc}" for doc, meta in zip(papers_results['documents'][0], papers_results['metadatas'][0])
    ])
    kg_context = "\n".join([
        f"{meta['head']} -[{meta['relation']}]-> {meta['tail']}" for meta in kg_results['metadatas'][0]
    ])
    final_prompt = f"""
请你作为一名专业的论文搜索与知识图谱问答助手，结合以下论文内容和知识图谱信息，**紧密围绕用户原始问题进行高质量、聚焦的回答**。

【用户问题】
{conversation.messages[-1].content}

【相关论文内容】
{context}

【相关知识图谱三元组】
{kg_context}

【作答要求】
1. 回答必须紧扣用户原始问题，避免泛泛而谈或仅堆砌信息。
2. 如有多条信息，请优先列出与问题最相关的要点，按相关性排序，分点作答。
3. 回答前请用一句话重述用户问题，确保聚焦。
4. 如有不足或无法直接回答的地方，请说明原因。
"""

    # 4. 再次调用LLM生成最终答案
    final_resp = requests.post(f'{URL}/chat/completions', json={
        'model': MODEL,
        'stream': False,
        'messages': [
            {"role": "system", "content": "你是一个论文搜索系统的ai工具。"},
            {"role": "user", "content": final_prompt}
        ],
    }, stream=False, timeout=60)
    final_answer = final_resp.json()['choices'][0]['message']['content']

    # 5. 组装前端需要的结构
    kg_triples = [
        {
            "head": meta.get("head", ""),
            "relation": meta.get("relation", ""),
            "tail": meta.get("tail", ""),
            "paper_id": meta.get("paper_id", ""),
            "source": meta.get("source", "")
        }
        for meta in kg_results['metadatas'][0]
    ] if kg_results['metadatas'] else []
    # 生成kg_matches用于高亮（embedding相似度匹配）
    def split_sentences(text):
        sents = re.split(r'(?<=[。！？.!?])|\n', text)
        return [s.strip() for s in sents if s.strip()]

    def get_embeddings(texts):
        url = "http://10.176.64.152:11435/v1/embeddings"
        resp = requests.post(url, json={"model": "bge-m3", "input": texts})
        return [d['embedding'] for d in resp.json()["data"]]

    def cosine_sim(a, b):
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def find_kg_matches_by_embedding(final_answer, kg_triples, threshold=0.5):
        sents = split_sentences(final_answer)
        if not sents: return []
        sent_embs = get_embeddings(sents)
        matches = []
        for triple in kg_triples:
            triple_text = f"{triple['head']} {triple['relation']} {triple['tail']} {triple['source']}"
            triple_emb = get_embeddings([triple_text])[0]
            # 计算与每个句子的相似度
            for i, sent_emb in enumerate(sent_embs):
                sim = cosine_sim(triple_emb, sent_emb)
                if sim > threshold:
                    matches.append({
                        'matched_section': sents[i],
                        'head': triple['head'],
                        'relation': triple['relation'],
                        'tail': triple['tail'],
                        'source': triple['source'],
                        'score': sim
                    })
                    break  # 一个三元组只高亮一次
        return matches

    kg_matches = find_kg_matches_by_embedding(final_answer, kg_triples, threshold=0.7)
    return {
        "response": final_answer,
        "papers": papers,
        "matches": [],
        "kg_triples": kg_triples,
        "kg_matches": kg_matches
    }


@app.post("/chat/", response_model=schemas.ConversationResponse)
async def chat(conversation: schemas.Conversation):
    # Add prompt prefix to user messages
    processed_messages = []
    for msg in conversation.messages:
        if msg.role == 'user':
            processed_msg = msg.model_dump()
            processed_msg['content'] = f"你是一个论文搜索系统的ai工具，下面是对你的提问：{msg.content}"
            processed_messages.append(processed_msg)
        else:
            processed_messages.append(msg.model_dump())
            
    resp = requests.post(f'{URL}/chat/completions', json={
        'model': MODEL,
        'stream': False,
        'messages': processed_messages,
    }, stream=False, timeout=60)
    return resp.json()


# Paper processing endpoints
@app.post("/papers/embed", response_model=schemas.PaperEmbedResponse)
async def embed_paper(paper: schemas.PaperEmbedRequest):
    if not papers_collection:
        raise HTTPException(
            status_code=500,
            detail="Vector database not available"
        )
    
    try:
        # Generate embedding for paper content
        combined_text = f"Title: {paper.title}\nAbstract: {paper.abstract}\nKeywords: {', '.join(paper.keywords)}"
        
        # Store in vector database (embedding is automatically generated)
        papers_collection.add(
            ids=[str(paper.paper_id)],
            documents=[combined_text],
            metadatas=[{
                "title": paper.title,
                "paper_id": paper.paper_id,
                "processed": True
            }]
        )
        
        # Get the stored embedding
        result = papers_collection.get(ids=[str(paper.paper_id)], include=["embeddings"])
        embedding = result["embeddings"][0] if result["embeddings"] else None
        
        return schemas.PaperEmbedResponse(
            paper_id=paper.paper_id,
            status="completed",
            embedding=embedding
        )
        
    except Exception as e:
        print(f"Failed to embed paper: {e}")
        return schemas.PaperEmbedResponse(
            paper_id=paper.paper_id,
            status="failed",
            embedding=None
        )


@app.post("/papers/vector-search", response_model=schemas.VectorSearchResponse)
async def vector_search(request: schemas.VectorSearchRequest):
    if not papers_collection:
        raise HTTPException(
            status_code=500,
            detail="Vector database not available"
        )
    
    try:
        # Perform vector search
        results = papers_collection.query(
            query_texts=[request.query],
            n_results=request.limit,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "paper_id": results["metadatas"][0][i]["paper_id"],
                "title": results["metadatas"][0][i]["title"],
                "content": results["documents"][0][i],
                "distance": results["distances"][0][i]
            })
        
        return schemas.VectorSearchResponse(
            results=formatted_results,
            search_time=0.0
        )
        
    except Exception as e:
        print(f"Vector search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Vector search failed"
        )


@app.post("/papers/recommend", response_model=schemas.PaperRecommendResponse)
async def recommend_papers(request: schemas.PaperRecommendRequest):
    if not papers_collection:
        raise HTTPException(
            status_code=500,
            detail="Vector database not available"
        )
    
    try:
        print(f"Recommendation request received for papers: {request.paper_ids}")
        
        # Get user's interacted papers
        if not request.paper_ids:
            print("No paper IDs provided, returning random papers")
            all_papers = papers_collection.get()
            print(f"Total papers in DB: {len(all_papers['ids'])}")
            
            if not all_papers["ids"]:
                raise HTTPException(
                    status_code=404,
                    detail="No papers available in database"
                )
                
            # Get random papers
            import random
            random_ids = random.sample(all_papers["ids"], min(request.limit, len(all_papers["ids"])))
            print(f"Selected random paper IDs: {random_ids}")
            results = papers_collection.get(ids=random_ids)
        else:
            print(f"Looking for embeddings for papers: {request.paper_ids}")
            # Get embeddings for user's interacted papers
            interacted_papers = papers_collection.get(
                ids=[str(pid) for pid in request.paper_ids],
                include=["embeddings"]
            )
            print(f"Found interacted papers: {interacted_papers}")
            
            if not interacted_papers["embeddings"]:
                print("No embeddings found, falling back to random papers")
                all_papers = papers_collection.get()
                random_ids = random.sample(all_papers["ids"], min(request.limit, len(all_papers["ids"])))
                results = papers_collection.get(ids=random_ids)
            else:
                print("Calculating average embedding")
                # Calculate average embedding of interacted papers
                avg_embedding = [
                    sum(emb) / len(emb) 
                    for emb in zip(*interacted_papers["embeddings"])
                ]
                print(f"Average embedding: {avg_embedding[:5]}...")
                
                # Search similar papers
                print("Querying similar papers")
                results = papers_collection.query(
                    query_embeddings=[avg_embedding],
                    n_results=request.limit,
                    include=["metadatas", "distances"]
                )
                print(f"Query results: {results}")
        
        # Format recommendations with strict validation
        recommendations = []
        valid_papers = papers_collection.get()
        print(f"Valid papers in collection: {len(valid_papers['ids'])}")
        
        if "metadatas" in results and results["metadatas"]:
            for i in range(len(results["ids"][0])):
                if not results["metadatas"][0][i] or "paper_id" not in results["metadatas"][0][i]:
                    print(f"Invalid metadata for paper {results['ids'][0][i]}")
                    continue
                    
                paper_id = results["metadatas"][0][i]["paper_id"]
                print(f"Checking paper ID: {paper_id}")
                
                # Verify paper exists in collection
                if paper_id not in valid_papers["ids"]:
                    print(f"Paper ID {paper_id} not found in collection")
                    continue
                
                # Ensure required fields exist
                if "title" not in results["metadatas"][0][i]:
                    print(f"Missing title for paper {paper_id}")
                    continue
                    
                recommendations.append({
                    "paper_id": paper_id,
                    "title": results["metadatas"][0][i]["title"],
                    "score": 1 - results["distances"][0][i] if results.get("distances") else 1.0
                })
            
        print(f"Final recommendations: {recommendations}")
        
        if not recommendations:
            error_msg = "No valid recommendations found after validation"
            print(error_msg)
            raise HTTPException(
                status_code=404,
                detail=error_msg
            )
        
        return schemas.PaperRecommendResponse(
            recommendations=recommendations,
            recommendation_time=0.0
        )
        
    except Exception as e:
        print(f"Recommendation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Recommendation failed"
        )


@app.post("/kg/vector-search", response_model=schemas.KGTripleSearchResponse)
async def kg_vector_search(request: schemas.KGTripleSearchRequest):
    try:
        kg_collection = chroma_client.get_or_create_collection("kg_triples")
        results = kg_collection.query(
            query_texts=[request.query],
            n_results=request.limit,
            include=["documents", "metadatas", "distances"]
        )
        triples = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            triples.append(schemas.KGTriple(
                head=meta["head"],
                relation=meta["relation"],
                tail=meta["tail"],
                paper_id=meta["paper_id"],
                source=meta["source"]
            ))
        return schemas.KGTripleSearchResponse(
            results=triples,
            search_time=0.0
        )
    except Exception as e:
        print(f"KG vector search failed: {e}")
        raise HTTPException(status_code=500, detail="KG vector search failed")
