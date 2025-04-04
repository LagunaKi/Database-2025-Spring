import chromadb
import chromadb.utils.embedding_functions as embedding_functions

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="API_KEY_IS_NOT_NEEDED",
    api_base="http://10.176.64.152:11435/v1",
    model_name="bge-m3"
)

# 注意：需要先启动向量数据库，参考README.md
client = chromadb.HttpClient(host='localhost', port=8002)

# 获取已存在的papers collection
collection = client.get_collection(name="papers", embedding_function=openai_ef)

# 验证集合中的论文数量
print(f"Papers in collection: {collection.count()}")

# 查询示例
if collection.count() > 0:
    # 获取第一个论文的ID
    first_paper = collection.get(limit=1)
    if first_paper['ids']:
        paper_id = first_paper['ids'][0]
        print(f"\nFirst paper details (ID: {paper_id}):")
        print(collection.get(ids=[paper_id]))
        
        # 示例向量搜索
        print("\nRunning sample vector search:")
        results = collection.query(
            query_texts=["machine learning"],
            n_results=3
        )
        print(f"Found {len(results['ids'][0])} relevant papers")

# 其他操作请参考文档：
# https://docs.trychroma.com/docs/overview/introduction