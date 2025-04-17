# 论文搜索助手
【基础要求】根据用户提问，系统从论文（PDF文档）库中搜索论文，并总结回答用户问题
【主要界面】主页含对话框（右上），聊天页含对话框、回答和论文列表（右下），点击论文查看论文详情

# 要求
除本项目提供的模型API外，不得调用其他外部API
系统符合分层架构设计要求
界面使用Vue，业务层和算法层使用FastAPI  
三层架构：
- 界面：`frontend`
- 业务层：`backend`
- 算法层：`backend_algo`

# 部署和使用方法
### 更新数据库
爬取论文：
``` bash
python backend_algo/arxiv_crawler.py
```  

处理论文向量并存储到ChromaDB：
``` bash
python backend_algo/batch_embed.py
```  
### 启动命令
在git bash运行
``` bash
chmod +x start_dev.sh
./start_dev.sh
```

在前端启动好之后（跳出前端链接），即可使用。  
前端链接（以控制台输出为准）：http://localhost:5173/  

打开后，注册并登录，进入“聊天”页面，在对话框输入问题（最好和NLP, AI, ML相关，因为目前只爬取了这些领域的论文），搜索后等待片刻，即可得到大模型文字回答和右方相关论文列表，点击论文即可查看详情，并且能得到其它论文推荐（根据用户最近的论文查看行为推荐）。

# 代码结构

## 系统架构
采用三层架构设计：
1. **前端层(frontend)**: Vue 3 + TypeScript实现用户界面
2. **业务层(backend)**: FastAPI实现业务逻辑和API接口
3. **算法层(backend_algo)**: 论文爬取、向量化和推荐算法

## 目录结构

### 前端层(frontend/src)
- `components/`: Vue组件
  - `Chat.vue`: 聊天和论文搜索界面
  - `PaperDetail.vue`: 论文详情展示
  - `LoginForm.vue`: 登录表单
  - `RegisterForm.vue`: 注册表单
- `pages/`: 页面路由组件
  - `Index.vue`: 主界面
  - `Login.vue`: 登录页
  - `Register.vue`: 注册页
- `router/`: 路由配置
- `request/`: API请求封装
  - `api.ts`: 接口定义
  - `http.ts`: HTTP请求封装
- `store/`: 状态管理(Pinia)
  - `user.ts`: 用户状态管理

### 业务层(backend)
- `models.py`: 数据模型定义(User, Paper等)
- `main.py`: FastAPI应用和路由
- `database.py`: 数据库连接配置
- `crud.py`: 数据库操作
- `schemas.py`: Pydantic模型
- `security.py`: 认证和安全

主要API接口:
- 用户认证: `/api/token`
- 论文搜索: `/api/papers/search`
- 论文详情: `/api/papers/{paper_id}`
- 论文推荐: `/api/recommendations/{paper_id}`
- 用户行为记录: `/api/papers/{paper_id}/interact`

### 算法层(backend_algo)
- `arxiv_crawler.py`: arXiv论文爬取
  - 从arXiv API获取论文元数据
  - 支持NLP/AI/ML领域论文
  - 保存到SQL数据库
- `batch_embed.py`: 论文向量化处理
  - 使用bge-m3模型生成嵌入向量
  - 存储到ChromaDB向量数据库
- `test_*.py`: 各模块测试

## 数据流
1. 用户在前端输入问题
2. 前端调用`/api/chat`接口
3. 后端:
   - 将问题向量化
   - 从ChromaDB搜索相似论文
   - 调用本地LLM生成回答
4. 返回回答和相关论文列表
5. 用户点击论文时记录行为
6. 基于用户行为生成推荐
