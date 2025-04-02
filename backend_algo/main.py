from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from backend_algo import schemas
import requests
import chromadb
import chromadb.utils.embedding_functions as embedding_functions


app = FastAPI()

# Initialize ChromaDB client
try:
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
except Exception as e:
    print(f"Failed to initialize ChromaDB client: {e}")
    papers_collection = None


URL = 'http://10.176.64.152:11434/v1'
MODEL = 'qwen2.5:7b'


@app.post("/chat/stream/")
async def chat_stream(conversation: schemas.Conversation):

    def generator():
        with requests.post(f'{URL}/chat/completions', json={
            'model': MODEL,
            'stream': True,
            'messages': [m.model_dump() for m in conversation.messages],
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


@app.post("/chat/", response_model=schemas.ConversationResponse)
async def chat(conversation: schemas.Conversation):
    resp = requests.post(f'{URL}/chat/completions', json={
        'model': MODEL,
        'stream': False,
        'messages': [m.model_dump() for m in conversation.messages],
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
        # Get user's interacted papers
        if not request.paper_ids:
            # If no interaction history, return popular papers
            results = papers_collection.query(
                query_texts=[""],
                n_results=request.limit,
                include=["metadatas"]
            )
        else:
            # Get embeddings for user's interacted papers
            interacted_papers = papers_collection.get(
                ids=[str(pid) for pid in request.paper_ids],
                include=["embeddings"]
            )
            
            if not interacted_papers["embeddings"]:
                # Fallback to popular papers if no embeddings found
                results = papers_collection.query(
                    query_texts=[""],
                    n_results=request.limit,
                    include=["metadatas"]
                )
            else:
                # Calculate average embedding of interacted papers
                avg_embedding = [
                    sum(emb) / len(emb) 
                    for emb in zip(*interacted_papers["embeddings"])
                ]
                
                # Search similar papers
                results = papers_collection.query(
                    query_embeddings=[avg_embedding],
                    n_results=request.limit,
                    include=["metadatas", "distances"]
                )
        
        # Format recommendations
        recommendations = []
        for i in range(len(results["ids"][0])):
            recommendations.append({
                "paper_id": results["metadatas"][0][i]["paper_id"],
                "title": results["metadatas"][0][i]["title"],
                "score": 1 - results["distances"][0][i] if results.get("distances") else 1.0
            })
        
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
