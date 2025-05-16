import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import random
import argparse

# 默认配置
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 8002

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="API_KEY_IS_NOT_NEEDED",
    api_base="http://10.176.64.152:11435/v1",
    model_name="bge-m3"
)

def check_collection(collection_name, host=DEFAULT_HOST, port=DEFAULT_PORT, sample=5):
    client = chromadb.HttpClient(host=host, port=port)
    collection = client.get_collection(name=collection_name, embedding_function=openai_ef)
    total = collection.count()
    print(f"Collection '{collection_name}' 总数: {total}")
    if total == 0:
        print("（无数据）")
        return
    # 随机抽取 sample 条
    all_ids = collection.get()["ids"]
    sample_ids = random.sample(all_ids, min(sample, len(all_ids)))
    print(f"\n随机抽取 {len(sample_ids)} 条:")
    docs = collection.get(ids=sample_ids, include=["documents", "metadatas"])
    for i, (doc, meta) in enumerate(zip(docs["documents"], docs["metadatas"])):
        print(f"--- {i+1} ---")
        if collection_name == "kg_triples":
            print(f"三元组: {meta.get('head', '')} -[{meta.get('relation', '')}]-> {meta.get('tail', '')}")
            print(f"来源论文: {meta.get('paper_id', '')}")
            print(f"原始片段: {meta.get('source', '')}")
        elif collection_name == "papers":
            print(f"论文ID: {meta.get('paper_id', meta.get('id', ''))}")
            print(f"标题: {meta.get('title', '')}")
            print(f"文档摘要片段: {doc[:100]}...")
        else:
            print(f"元数据: {meta}")
            print(f"文档片段: {doc[:100]}...")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="检查ChromaDB向量库内容")
    parser.add_argument('--collection', type=str, default='kg_triples', choices=['kg_triples', 'papers'], help='要检查的collection名称')
    parser.add_argument('--host', type=str, default=DEFAULT_HOST, help='ChromaDB服务host')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='ChromaDB服务port')
    parser.add_argument('--sample', type=int, default=5, help='随机抽取条数')
    args = parser.parse_args()
    check_collection(args.collection, host=args.host, port=args.port, sample=args.sample) 