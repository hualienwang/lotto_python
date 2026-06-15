import os
import sys

# 將專案根目錄和 backend 目錄加入 Python 路徑
# 這確保了 backend/main.py 中的 "from database import ..." 可以運作
root_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "backend"))

from backend.main import app

# Vercel 需要一個名為 app 的對象
# 如果 backend.main 中的是 app，則直接使用
