#!/bin/bash
set -e  # Exit immediately if any command fails
eval "$(conda shell.bash hook)"

# 设置绝对路径的PYTHONPATH
PROJECT_ROOT=$(pwd)
export PYTHONPATH=$PROJECT_ROOT:$PYTHONPATH

# 启动向量数据库(先启动依赖服务)
echo "Starting ChromaDB vector database..."
conda activate fastapi
cd backend_algo && chroma run --path ./data_vector_db --host localhost --port 8002 &
sleep 5  # 等待向量数据库初始化

# 检查向量数据库是否启动
if ! curl -s http://localhost:8002/api/v1/heartbeat >/dev/null; then
    echo "Failed to start ChromaDB"
    exit 1
fi

# 启动算法层服务
echo "Starting algorithm service..."
conda activate fastapi
cd $PROJECT_ROOT && uvicorn backend_algo.main:app --port 8001 --reload &
sleep 3  # 等待算法服务初始化

# 检查算法服务是否启动
if ! curl -s http://localhost:8001/health >/dev/null; then
    echo "Failed to start algorithm service"
    exit 1
fi

# 启动业务层后端
echo "Starting backend service..."
conda activate fastapi
cd $PROJECT_ROOT && uvicorn backend.main:app --port 8000 --reload --workers 1 --no-access-log &
sleep 3  # 等待后端服务初始化

# 检查后端服务是否启动
if ! curl -s http://localhost:8000/health >/dev/null; then
    echo "Failed to start backend service"
    exit 1
fi

# 最后启动前端
echo "Starting frontend..."
cd frontend && npm run dev

wait