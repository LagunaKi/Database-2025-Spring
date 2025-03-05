# 后端（算法层）：FastAPI

算法层调用大模型，不需要连关系数据库。

## 环境

后端使用conda管理环境：
```shell
conda create -n fastapi python=3.12
pip install -r requirements.txt
```

## 数据库

无

## 启动

启动：
```shell
uvicorn main:app --port 8001
```

文档页面：`http://127.0.0.1:8001/docs`
