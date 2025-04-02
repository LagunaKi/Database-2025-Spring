import time
import schedule
from datetime import datetime
from arxiv_crawler import sync_arxiv_papers

def job():
    print(f"[{datetime.now()}] Starting arXiv sync...")
    try:
        sync_arxiv_papers()
        print(f"[{datetime.now()}] Sync completed successfully")
    except Exception as e:
        print(f"[{datetime.now()}] Sync failed: {str(e)}")

def run_scheduler():
    # Schedule daily at 2:00 AM
    schedule.every().day.at("02:00").do(job)
    
    print("arXiv sync service started. Scheduled to run daily at 2:00 AM")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    run_scheduler()
