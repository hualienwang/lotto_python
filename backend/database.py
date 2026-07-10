from sqlmodel import SQLModel, create_engine, Session, select
from typing import Generator
import os

# 資料庫路徑
import os
from pathlib import Path

# 獲取專案路徑
BASE_DIR = Path(__file__).resolve().parent.parent

# 優先使用環境變數中的 DATABASE_URL (可用於 Vercel Postgres)
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # 如果沒有環境變數，使用 SQLite
    db_name = "lotto.db"
    
    # 在 Vercel 上，檔案是唯讀的，但在某些情況下我們可能需要將其複製到 /tmp
    # 這裡我們優先檢查幾個可能的位置
    db_paths = [
        Path(os.getcwd()) / db_name,
        BASE_DIR / "backend" / db_name,
        BASE_DIR / db_name
    ]
    
    final_db_path = db_paths[0] # 預設
    for p in db_paths:
        if p.exists():
            final_db_path = p
            break
            
    DATABASE_URL = f"sqlite:///{final_db_path}"

# 創建引擎
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

def get_session() -> Generator[Session, None, None]:
    """取得資料庫會話"""
    with Session(engine) as session:
        yield session

def init_db():
    """初始化資料庫表"""
    # 如果是 SQLite，檢查是否需要從其他地方複製
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            # 嘗試找尋備用路徑
            for p in [BASE_DIR / "backend" / "lotto.db", BASE_DIR / "lotto.db"]:
                if p.exists() and str(p) != db_path:
                    import shutil
                    try:
                        shutil.copy(p, db_path)
                        break
                    except Exception:
                        pass
    
    # 創建所有表
    # 在 Vercel 上這步可能會因為唯讀而失敗，所以加個 try
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        print(f"資料庫初始化警告 (可能在唯讀環境): {e}")
    
    # 嘗試新增 numbers2 欄位（如果表已經存在）
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # 檢查欄位是否存在
            result = conn.execute(text("PRAGMA table_info(predictions)"))
            columns = [row[1] for row in result]
            if "numbers2" not in columns:
                conn.execute(text("ALTER TABLE predictions ADD COLUMN numbers2 VARCHAR DEFAULT NULL"))
                conn.commit()
    except Exception as e:
        # 在唯讀環境中這很正常
        pass
