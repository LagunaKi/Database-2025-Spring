import sys
from pathlib import Path
import json
from pprint import pprint

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from backend.database import SessionLocal
from backend.models import Paper

def check_paper(paper_id):
    db = SessionLocal()
    try:
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if paper:
            print("=== 论文数据详情 ===")
            print(f"ID: {paper.id}")
            print(f"标题: {paper.title}")
            print(f"作者数据类型: {type(paper.authors)}")
            print(f"作者数据内容: {paper.authors}")
            print(f"摘要存在: {paper.abstract is not None}")
            print(f"PDF URL: {paper.pdf_url}")
            print(f"关键词: {paper.keywords}")
            print(f"发表日期: {paper.published_date}")
            
            # 检查数据是否符合前端接口要求
            required_fields = ['id', 'title', 'authors', 'abstract', 'pdf_url']
            missing_fields = [field for field in required_fields if getattr(paper, field) is None]
            if missing_fields:
                print(f"⚠️ 缺少必填字段: {missing_fields}")
            else:
                print("✅ 所有必填字段完整")
                
            # 检查authors是否为列表
            if not isinstance(paper.authors, list):
                print(f"⚠️ authors字段不是列表类型: {type(paper.authors)}")
        else:
            print(f"❌ 未找到ID为 {paper_id} 的论文")
    except Exception as e:
        print(f"检查论文时出错: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check_paper("2503.11827v1")
