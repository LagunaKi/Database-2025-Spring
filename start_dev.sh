#!/bin/bash
eval "$(conda shell.bash hook)"  # 新增关键初始化命令

# 前端
cd frontend && npm run dev &

# 业务层后端
conda activate fastapi
cd backend && uvicorn main:app --port 8000 --reload &

# 向量数据库
conda activate fastapi
cd backend_algo && chroma run --path ./data_vector_db --host localhost --port 8002 &

# 算法层
conda activate fastapi
cd backend_algo && uvicorn main:app --port 8001 --reload &

wait