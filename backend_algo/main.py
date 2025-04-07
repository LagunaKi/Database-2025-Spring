from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from backend_algo import schemas
import requests
import chromadb
import chromadb.utils.embedding_functions as embedding_functions


app = FastAPI()

# Initialize ChromaDB client with persistent mode
chroma_client = None
papers_collection = None
try:
    print("Initializing ChromaDB in persistent mode...")
    chroma_client = chromadb.PersistentClient(
        path="chroma_data",
        settings=chromadb.config.Settings(allow_reset=True)
    )
    
    # Verify connection
    print("ChromaDB initialized in persistent mode")
    
    # Get or create collection
    papers_collection = chroma_client.get_or_create_collection("papers")
    print("Successfully connected to ChromaDB collection")
except Exception as e:
    print(f"Failed to initialize ChromaDB: {str(e)}")
    papers_collection = None


URL = 'http://10.176.64.152:11434/v1'
MODEL = 'qwen2.5:7b'


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
