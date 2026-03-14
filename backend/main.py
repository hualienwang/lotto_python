from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# 天干地支對應
HEAVENLY_STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
EARTHLY_BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 傳統吉時 (根據天干地支)
LUCKY_HOURS = {
    '甲': [7, 9, 11],
    '乙': [6, 8, 10],
    '丙': [9, 11, 13],
    '丁': [8, 10, 12],
    '戊': [7, 9, 11],
    '己': [6, 8, 10],
    '庚': [9, 11, 15],
    '辛': [8, 10, 14],
    '壬': [7, 11, 13],
    '癸': [6, 10, 12]
}

# 吉號對應 (根據天干)
LUCKY_NUMBERS = {
    '甲': [1, 13, 25, 37],
    '乙': [2, 14, 26, 38],
    '丙': [3, 15, 27, 39],
    '丁': [4, 16, 28],
    '戊': [5, 17, 29],
    '己': [6, 18, 30],
    '庚': [7, 19, 31],
    '辛': [8, 20, 32],
    '壬': [9, 21, 33],
    '癸': [10, 22, 34]
}

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
    """取得預測號碼"""
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
    
    # 排序取得熱門號碼
    sorted_nums = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
    hot_numbers = [n[0] for n in sorted_nums[:10]]
    
    # 生成預測號碼
    prediction = generate_prediction(hot_numbers, frequency)
    
    data = {
        "numbers": prediction,
        "analysis": {
            "hot_numbers": hot_numbers,
            "frequency": frequency
        }
    }
    
    return ApiResponse(success=True, data=data)


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
    session: Session = Depends(get_session)
):
    """儲存預測"""
    prediction = Prediction(period=period, numbers=numbers)
    session.add(prediction)
    session.commit()
    
    return ApiResponse(success=True, message="預測已儲存", data={"id": prediction.id})


# ============ 天干地支預測 API ============

def get_tiangan_dizhi(date=None):
    """取得指定日期的天干地支"""
    if date is None:
        date = datetime.now()
    
    year = date.year
    
    # 計算天干 (以1984年為基準甲子年)
    tg_idx = (year - 1984) % 10
    # 計算地支
    dz_idx = (year - 1984) % 12
    
    return HEAVENLY_STEMS[tg_idx], EARTHLY_BRANCHES[dz_idx], year

def get_lucky_hour(tg):
    """根據天干取得吉時"""
    return LUCKY_HOURS.get(tg, [9, 11, 13])

def is_draw_day(date):
    """檢查是否為開獎日 (星期一至六，星期日不開獎)"""
    return date.weekday() != 6

def get_best_prediction_time(date=None):
    """計算最佳預測時間"""
    if date is None:
        date = datetime.now()
    
    # 如果當天不是開獎日，找下一個開獎日
    while not is_draw_day(date):
        date = date + timedelta(days=1)
    
    tg, dz, year = get_tiangan_dizhi(date)
    lucky_hours = get_lucky_hour(tg)
    
    current_hour = date.hour
    
    # 找下一個最近的吉時
    best_hour = None
    for hour in lucky_hours:
        if hour > current_hour:
            best_hour = hour
            break
    
    # 如果沒有未來的吉時，使用第一個吉時
    if best_hour is None:
        best_hour = lucky_hours[0]
        date = date + timedelta(days=1)
        # 確保新日期是開獎日
        while not is_draw_day(date):
            date = date + timedelta(days=1)
    
    prediction_time = date.replace(hour=best_hour, minute=0, second=0, microsecond=0)
    
    return {
        'date': date.strftime('%Y-%m-%d'),
        'time': f'{best_hour:02d}:00',
        'tiangan': tg,
        'dizhi': dz,
        'lucky_hours': lucky_hours,
        'is_draw_day': is_draw_day(date)
    }

def generate_tiangan_prediction_numbers():
    """生成天干地支預測號碼"""
    # 模擬熱門號碼 (實際應從資料庫獲取)
    hot_numbers = [5, 12, 18, 23, 34, 37, 39, 8, 15, 27]
    
    selected = set()
    
    # 選擇 1-2 個熱門號碼
    hot_count = random.randint(1, 2)
    for _ in range(hot_count):
        selected.add(random.choice(hot_numbers))
    
    # 填充至5個號碼
    while len(selected) < 5:
        num = random.randint(1, 39)
        selected.add(num)
    
    result = sorted(selected)
    return ', '.join([str(n).zfill(2) for n in result])

def get_lucky_numbers_by_tiangan(tg):
    """根據天干取得當日吉號"""
    # 取得天干對應的吉號
    base_numbers = LUCKY_NUMBERS.get(tg, [1, 2, 3, 4, 5])
    
    # 加入一些相關號碼 (根據傳統選擇)
    additional = []
    for num in base_numbers:
        # 加入同尾數的號碼
        for i in range(1, 4):
            candidate = num + i * 10
            if 1 <= candidate <= 39:
                additional.append(candidate)
    
    # 合併並去重
    all_numbers = list(set(base_numbers + additional))
    
    # 隨機選擇5個號碼
    selected = random.sample(all_numbers, min(5, len(all_numbers)))
    
    return sorted(selected)

@app.get("/api/prediction/tiangan", response_model=ApiResponse)
def get_tiangan_prediction():
    """取得天干地支預測"""
    now = datetime.now()
    
    # 取得天干
    tg, dz, year = get_tiangan_dizhi(now)
    lucky_hours = get_lucky_hour(tg)
    
    # 檢查今天是否開獎日
    if not is_draw_day(now):
        # 找下一個開獎日
        next_day = now + timedelta(days=1)
        while not is_draw_day(next_day):
            next_day = next_day + timedelta(days=1)
        prediction_date = next_day.strftime('%Y-%m-%d')
        tg_next, dz_next, _ = get_tiangan_dizhi(next_day)
        lucky_hours = get_lucky_hour(tg_next)
        tg = tg_next
        dz = dz_next
    else:
        # 今天開獎，使用今天的日期
        prediction_date = now.strftime('%Y-%m-%d')
    
    # 產生隨機預測號碼
    prediction_numbers = generate_tiangan_prediction_numbers()
    
    # 取得當日吉時號碼（參考用）
    lucky_reference = get_lucky_numbers_by_tiangan(tg)
    lucky_reference_str = ', '.join([str(n).zfill(2) for n in lucky_reference])
    
    # 組合預測資訊
    data = {
        'prediction_date': prediction_date,
        'prediction_time': f'{lucky_hours[0]:02d}:00',
        'tiangan_dizhi': f"{tg}{dz}",
        'tiangan': tg,
        'dizhi': dz,
        'lucky_hours': lucky_hours,
        'numbers': prediction_numbers,
        'lucky_reference_numbers': lucky_reference_str,
        'is_draw_day': is_draw_day(now),
        'created_at': now.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 保存到 prediction_result.json
    save_tiangan_prediction(data)
    
    return ApiResponse(success=True, data=data)


def save_tiangan_prediction(prediction_info, output_file='prediction_result.json'):
    """保存天干地支預測結果到檔案（追加方式）"""
    filepath = Path(output_file)
    
    # 讀取現有資料
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {'predictions': []}
    
    # 追加新預測
    data['predictions'].append(prediction_info)
    
    # 保持最近30筆
    data['predictions'] = data['predictions'][-30:]
    
    # 寫入檔案
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath


# ============ 統計 API ============

@app.get("/api/statistics", response_model=ApiResponse)
def get_statistics(session: Session = Depends(get_session)):
    """取得統計數據"""
    results = session.exec(
        select(LotteryResult).order_by(LotteryResult.id.desc()).limit(30)
    ).all()
    
    if not results:
        return ApiResponse(success=False, message="尚無資料")
    
    frequency = {}
    odd_even = {"odd": 0, "even": 0}
    ranges = {"1-10": 0, "11-20": 0, "21-30": 0, "31-39": 0}
    
    for r in results:
        nums = [int(n.strip()) for n in r.numbers.split(",")]
        for num in nums:
            frequency[num] = frequency.get(num, 0) + 1
            
            # 單雙統計
            if num % 2 == 0:
                odd_even["even"] += 1
            else:
                odd_even["odd"] += 1
            
            # 區間統計
            if num <= 10:
                ranges["1-10"] += 1
            elif num <= 20:
                ranges["11-20"] += 1
            elif num <= 30:
                ranges["21-30"] += 1
            else:
                ranges["31-39"] += 1
    
    data = {
        "frequency": frequency,
        "odd_even": odd_even,
        "ranges": ranges,
        "total_draws": len(results)
    }
    
    return ApiResponse(success=True, data=data)


# ============ 健康檢查 ============

@app.get("/")
def root():
    return {"message": "台灣彩券539 API 服務正常", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
