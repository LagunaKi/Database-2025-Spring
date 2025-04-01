import requests
import json

URL = "http://10.176.64.152:11436/v1/rerank"
MODEL = "bge-reranker-v2-m3"

response = requests.post(URL, json={
    "model": MODEL,
    "query": "What is the capital of France?",
    "documents": [
        "The capital of Brazil is Brasilia.",
        "The capital of France is Paris.",
        "Horses and cows are both animals",
    ],
    "top_n": 2,
})  # 从documents中查找与query最相关的top_n条文本

if response.status_code == 200:
    print("Request successful!")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Request failed with status code: {response.status_code}")
    print(response.text)