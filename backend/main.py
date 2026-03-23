from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from typing import List, Optional
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

from database import get_session, init_db, engine
from models import LotteryResult, Prediction, ApiResponse

# 創建 FastAPI 應用
app = FastAPI(title="台灣彩券539 API")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 路由 ============

@app.on_event("startup")
async def startup_event():
    """啟動時初始化資料庫"""
    init_db()
    # 如果資料庫為空，載入初始資料
    with Session(engine) as session:
        result = session.exec(select(LotteryResult).limit(1)).first()
        if not result:
            load_initial_data(session)


def load_initial_data(session: Session):
    """從 JSON 檔案載入初始資料"""
    # 嘗試從多個位置找到資料檔案
    possible_paths = [
        "lotto539_data.json",
        "../lotto539_data.json",
        "../lottery539/lotto539_data.json"
    ]
    
    data = None
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            break
    
    if data and "draws" in data:
        for draw in data["draws"]:
            # 解析日期
            date_parts = draw["date"].split("-")
            year = int(date_parts[0]) - 1911
            month = date_parts[1].zfill(2)
            day = date_parts[2].zfill(2)
            period = f"{year}{month}{day}"
            
            # 格式化號碼
            numbers = ", ".join([str(n).zfill(2) for n in draw["numbers"]])
            
            result = LotteryResult(
                period=period,
                numbers=numbers,
                draw_date=draw["date"]
            )
            session.add(result)
        
        session.commit()
        print(f"已載入 {len(data['draws'])} 筆初始資料")


# ============ 開獎結果 API ============

@app.get("/api/results", response_model=ApiResponse)
def get_results(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """取得開獎結果列表"""
    query = select(LotteryResult).order_by(LotteryResult.draw_date.desc()).limit(limit)
    
    if start_date:
        query = select(LotteryResult).where(LotteryResult.draw_date >= start_date).order_by(LotteryResult.draw_date.desc()).limit(limit)
    
    if start_date and end_date:
        query = select(LotteryResult).where(
            LotteryResult.draw_date >= start_date,
            LotteryResult.draw_date <= end_date
        ).order_by(LotteryResult.draw_date.desc()).limit(limit)
    
    results = session.exec(query).all()
    
    data = [
        {
            "id": r.id,
            "period": r.period,
            "numbers": r.numbers,
            "draw_date": r.draw_date,
            "created_at": r.created_at
        }
        for r in results
    ]
    
    return ApiResponse(success=True, data={"results": data, "total": len(data)})


@app.get("/api/results/latest", response_model=ApiResponse)
def get_latest_result(session: Session = Depends(get_session)):
    """取得最新開獎結果"""
    result = session.exec(
        select(LotteryResult).order_by(LotteryResult.id.desc()).limit(1)
    ).first()
    
    if not result:
        return ApiResponse(success=False, message="尚無開獎資料")
    
    data = {
        "id": result.id,
        "period": result.period,
        "numbers": result.numbers,
        "draw_date": result.draw_date,
        "created_at": result.created_at
    }
    
    return ApiResponse(success=True, data=data)


@app.post("/api/results", response_model=ApiResponse)
def add_result(
    period: str,
    numbers: str,
    draw_date: str,
    session: Session = Depends(get_session)
):
    """新增開獎結果"""
    # 檢查是否已存在
    existing = session.exec(
        select(LotteryResult).where(LotteryResult.period == period)
    ).first()
    
    if existing:
        return ApiResponse(success=False, message=f"期別 {period} 已經存在")
    
    result = LotteryResult(
        period=period,
        numbers=numbers,
        draw_date=draw_date
    )
    session.add(result)
    session.commit()
    
    return ApiResponse(success=True, message="開獎結果已新增", data={"id": result.id})


# ============ 預測 API ============

@app.get("/api/prediction", response_model=ApiResponse)
def get_prediction(session: Session = Depends(get_session)):
    """取得預測號碼 - 新演算法：
    1. 取得最近30期開獎號碼中出現次數大於等於4次的號碼（熱門號碼）
    2. 取得最近三期開獎號碼
    3. 從熱門號碼中減去最近三期開獎號碼（不重複）
    4. 從剩下的號碼中隨機選擇5個號碼作為預測（不加權）"""
    # 取得最近30期資料進行分析
    results = session.exec(
        select(LotteryResult).order_by(LotteryResult.id.desc()).limit(30)
    ).all()
    
    if not results:
        return ApiResponse(success=False, message="尚無足夠資料進行預測")
    
    # 統計號碼頻率
    frequency = {}
    for r in results:
        nums = [int(n.strip()) for n in r.numbers.split(",")]
        for num in nums:
            frequency[num] = frequency.get(num, 0) + 1
    
    # 篩選出現次數大於等於4次的號碼（熱門號碼）
    hot_numbers = [num for num, count in frequency.items() if count >= 4]
    
    if len(hot_numbers) < 5:
        # 如果不足5個號碼，則使用出現次數最多的前10個號碼
        sorted_nums = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
        hot_numbers = [n[0] for n in sorted_nums[:10]]
    
    # 取得最近三期開獎號碼
    recent_3_results = session.exec(
        select(LotteryResult).order_by(LotteryResult.id.desc()).limit(3)
    ).all()
    
    recent_3_numbers = set()
    for r in recent_3_results:
        nums = [int(n.strip()) for n in r.numbers.split(",")]
        recent_3_numbers.update(nums)
    
    # 從熱門號碼中減去最近三期開獎號碼
    filtered_numbers = [num for num in hot_numbers if num not in recent_3_numbers]
    
    # 如果過濾後不足5個號碼，從剩餘熱門號碼中补充
    if len(filtered_numbers) < 5:
        remaining_hot = [num for num in hot_numbers if num in recent_3_numbers]
        # 按頻率排序取最高頻率的
        remaining_hot_sorted = sorted(remaining_hot, key=lambda x: frequency.get(x, 0), reverse=True)
        filtered_numbers.extend(remaining_hot_sorted[:5 - len(filtered_numbers)])
    
    # 從過濾後的號碼中隨機選擇5個（不加權）
    import random
    final_pool = filtered_numbers[:]  # 複製一份避免修改原始列表
    random.shuffle(final_pool)
    prediction_set1 = sorted(final_pool[:5])
    
    # 產生第二組（再次隨機）
    random.shuffle(final_pool)
    prediction_set2 = sorted(final_pool[:5])
    
    # 準備分析資料
    frequency_analysis = {str(num): count for num, count in sorted(frequency.items(), key=lambda x: x[1], reverse=True)}
    
    data = {
        "numbers": ", ".join([str(n).zfill(2) for n in prediction_set1]),  # 第一組
        "numbers2": ", ".join([str(n).zfill(2) for n in prediction_set2]),  # 第二組
        "analysis": {
            "hot_numbers": sorted(hot_numbers),
            "recent_3_numbers": sorted(recent_3_numbers),
            "filtered_numbers": sorted(filtered_numbers),
            "frequency": frequency_analysis
        }
    }
    
    return ApiResponse(success=True, data=data)


def generate_prediction_sets(frequent_numbers: List[int], frequency: dict, sorted_simulation: List[tuple]) -> List[str]:
    """根據模擬結果產生2組539預測號碼"""
    predictions = []
    
    # 取得模擬中出現頻率最高的號碼
    top_numbers = [num for num, _ in sorted_simulation[:15]]
    
    for _ in range(2):
        selected = set()
        
        # 策略1: 選擇2-3個最高頻率的號碼
        top_count = random.randint(2, 3)
        available_top = [n for n in top_numbers if n not in selected]
        while len(selected) < top_count and available_top:
            chosen = random.choice(available_top)
            selected.add(chosen)
            available_top.remove(chosen)
        
        # 策略2: 填充至5個號碼，使用加權隨機
        weights = {}
        max_sim = max(sorted_simulation, key=lambda x: x[1])[1] if sorted_simulation else 1
        
        for num in range(1, 40):
            sim_count = dict(sorted_simulation).get(num, 0)
            weights[num] = (sim_count / max_sim) if max_sim > 0 else 0.1
        
        while len(selected) < 5:
            nums = list(range(1, 40))
            weight_list = [weights[n] for n in nums]
            chosen = random.choices(nums, weights=weight_list, k=1)[0]
            if chosen not in selected:
                selected.add(chosen)
        
        # 策略3: 確保奇偶平衡
        final_selection = list(selected)
        odd_count = sum(1 for n in final_selection if n % 2 == 1)
        
        if len(final_selection) == 5:
            if odd_count < 2:
                even_nums = [n for n in final_selection if n % 2 == 0]
                if even_nums:
                    final_selection.remove(random.choice(even_nums))
                    odd_pool = [n for n in range(1, 40) if n % 2 == 1 and n not in final_selection]
                    if odd_pool:
                        final_selection.append(random.choice(odd_pool[:10]))
            elif odd_count > 3:
                odd_nums = [n for n in final_selection if n % 2 == 1]
                if odd_nums:
                    final_selection.remove(random.choice(odd_nums))
                    even_pool = [n for n in range(1, 40) if n % 2 == 0 and n not in final_selection]
                    if even_pool:
                        final_selection.append(random.choice(even_pool[:10]))
        
        result = sorted(final_selection)[:5]
        predictions.append(", ".join([str(n).zfill(2) for n in result]))
    
    return predictions


def generate_prediction(hot_numbers: List[int], frequency: dict) -> str:
    """根據分析生成預測號碼 - 優化版"""
    import random
    
    # 計算每個號碼的權重 (結合熱門和冷門)
    weights = {}
    max_freq = max(frequency.values()) if frequency else 1
    min_freq = min(frequency.values()) if frequency else 0
    
    for num in range(1, 40):
        freq = frequency.get(num, 0)
        
        # 計算熱門權重 (出現次數越多權重越高)
        hot_weight = freq / max_freq if max_freq > 0 else 0
        
        # 計算冷門權重 (一段時間沒出現的號碼給予較高權重)
        # 這裡簡單用頻率低作為冷門指標
        cold_weight = 1 - (freq / max_freq) if max_freq > 0 else 1
        
        # 結合權重: 40% 熱門 + 30% 冷門 + 30% 均勻分布
        weights[num] = hot_weight * 0.4 + cold_weight * 0.3 + 0.3
    
    selected = set()
    
    # 策略1: 確保選擇 1-2 個熱門號碼
    hot_count = random.randint(1, 2)
    available_hot = [n for n in hot_numbers if n not in selected]
    while len(selected) < hot_count and available_hot:
        chosen = random.choice(available_hot)
        selected.add(chosen)
        available_hot.remove(chosen)
    
    # 策略2: 選擇 1 個冷門號碼 (低頻率但有機會開出)
    cold_numbers = sorted(frequency.items(), key=lambda x: x[1])[:10]
    cold_nums = [n[0] for n in cold_numbers if n[0] not in selected]
    if cold_nums and random.random() > 0.3:  # 70%機率選擇冷門號碼
        selected.add(random.choice(cold_nums[:5]))
    
    # 策略3: 填充至5個號碼，使用加權隨機
    while len(selected) < 5:
        # 根據權重隨機選擇
        nums = list(weights.keys())
        weight_list = [weights[n] for n in nums]
        chosen = random.choices(nums, weights=weight_list, k=1)[0]
        selected.add(chosen)
    
    # 策略4: 確保奇偶平衡 (2-3個奇數, 2-3個偶數)
    final_selection = list(selected)
    odd_count = sum(1 for n in final_selection if n % 2 == 1)
    
    if len(final_selection) == 5:
        if odd_count < 2:
            # 太少奇數，替換一個偶數為奇數
            even_nums = [n for n in final_selection if n % 2 == 0]
            if even_nums:
                final_selection.remove(random.choice(even_nums))
                # 加入一個奇數
                odd_pool = [n for n in range(1, 40) if n % 2 == 1 and n not in final_selection]
                if odd_pool:
                    final_selection.append(random.choice(odd_pool[:10]))
        elif odd_count > 3:
            # 太多奇數，替換一個奇數為偶數
            odd_nums = [n for n in final_selection if n % 2 == 1]
            if odd_nums:
                final_selection.remove(random.choice(odd_nums))
                # 加入一個偶數
                even_pool = [n for n in range(1, 40) if n % 2 == 0 and n not in final_selection]
                if even_pool:
                    final_selection.append(random.choice(even_pool[:10]))
    
    result = sorted(set(final_selection))[:5]
    return ", ".join([str(n).zfill(2) for n in result])


@app.post("/api/prediction", response_model=ApiResponse)
def save_prediction(
    period: str,
    numbers: str,
    numbers2: str = "",
    session: Session = Depends(get_session)
):
    """儲存預測"""
    try:
        prediction = Prediction(period=period, numbers=numbers, numbers2=numbers2 if numbers2 else None)
        session.add(prediction)
        session.commit()
        
        return ApiResponse(success=True, message="預測已儲存", data={"id": prediction.id})
    except Exception as e:
        session.rollback()
        # 嘗試只儲存 numbers
        try:
            prediction = Prediction(period=period, numbers=numbers)
            session.add(prediction)
            session.commit()
            return ApiResponse(success=True, message="預測已儲存(第一組)", data={"id": prediction.id})
        except Exception as e2:
            return ApiResponse(success=False, message=f"儲存失敗: {str(e)}")





# ============ 健康檢查 ============

# 配置靜態檔案服務
FRONTEND_DIST = "../frontend/dist"

@app.get("/")
def root():
    """首頁服務前端 index.html"""
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "台灣彩券539 API 服務正常", "version": "1.0.0"}

@app.get("/{path:path}")
def serve_frontend(path: str):
    """服務前端路由 - 讓 Vue Router 可以正常運作"""
    file_path = os.path.join(FRONTEND_DIST, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    # 如果檔案不存在，回傳 index.html 讓 Vue Router 處理
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Not found"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
