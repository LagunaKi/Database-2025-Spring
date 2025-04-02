# FastAPI + Vue 示例项目

三层架构：
- 界面：`frontend`
- 业务层：`backend`
- 算法层：`backend_algo`

# 论文搜索助手
【基础要求】根据用户提问，系统从论文（PDF文档）库中搜索论文，并总结回答用户问题
【主要界面】主页含对话框（右上），聊天页含对话框、回答和论文列表（右下），点击论文查看论文详情

# 要求
除本项目提供的模型API外，不得调用其他外部API
系统符合分层架构设计要求
界面使用Vue，业务层和算法层使用FastAPI

# 启动命令
在git bash运行
chmod +x start_dev.sh
./start_dev.sh

前端➜  Local:   http://localhost:5174/