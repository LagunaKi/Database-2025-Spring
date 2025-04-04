from backend.database import Base, engine
from backend import models
import chromadb
import chromadb.utils.embedding_functions as embedding_functions

def reset_database():
    # 先删除关联表
    print("Dropping user_paper_interactions table...")
    models.UserPaperInteraction.__table__.drop(engine)
    
    # 然后删除papers表
    print("Dropping papers table...")
    models.Paper.__table__.drop(engine)
    
    # 重建papers表
    print("Creating papers table...")
    models.Paper.__table__.create(engine)
    
    # 重建关联表
    print("Creating user_paper_interactions table...")
    models.UserPaperInteraction.__table__.create(engine)
    
    # 重置chromadb向量数据库
    print("\nResetting chromadb vector database...")
    chroma_success = False
    try:
        print("Connecting to chromadb...")
        client = chromadb.HttpClient(host='localhost', port=8002)
        print("Deleting existing collection...")
        client.delete_collection(name="papers")
        
        print("Creating new collection...")
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key="API_KEY_IS_NOT_NEEDED",
            api_base="http://10.176.64.152:11435/v1",
            model_name="bge-m3"
        )
        client.create_collection(name="papers", embedding_function=openai_ef)
        chroma_success = True
        print("Chromadb reset successfully!")
    except Exception as e:
        print(f"\nError resetting chromadb: {str(e)}")
        print("Please ensure chromadb service is running on localhost:8002")
        print("and embedding service is available at http://10.176.64.152:11435")
    
    print("\nDatabase reset summary:")
    print(f"- SQL tables reset: {'Success' if True else 'Failed'}")
    print(f"- Chromadb reset: {'Success' if chroma_success else 'Failed'}")
    if not chroma_success:
        print("\nNote: Chromadb reset failed but SQL tables were reset successfully.")
        print("You may need to manually restart chromadb service.")

if __name__ == "__main__":
    reset_database()

# 重置指令：python -m backend.db_reset