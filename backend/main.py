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
        "../lottery539/lotto539_data.json",
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
                period=period, numbers=numbers, draw_date=draw["date"]
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
    session: Session = Depends(get_session),
):
    """取得開獎結果列表"""
    query = select(LotteryResult).order_by(LotteryResult.draw_date.desc()).limit(limit)

    if start_date:
        query = (
            select(LotteryResult)
            .where(LotteryResult.draw_date >= start_date)
            .order_by(LotteryResult.draw_date.desc())
            .limit(limit)
        )

    if start_date and end_date:
        query = (
            select(LotteryResult)
            .where(
                LotteryResult.draw_date >= start_date,
                LotteryResult.draw_date <= end_date,
            )
            .order_by(LotteryResult.draw_date.desc())
            .limit(limit)
        )

    results = session.exec(query).all()

    data = [
        {
            "id": r.id,
            "period": r.period,
            "numbers": r.numbers,
            "draw_date": r.draw_date,
            "created_at": r.created_at,
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
        "created_at": result.created_at,
    }

    return ApiResponse(success=True, data=data)


@app.post("/api/results", response_model=ApiResponse)
def add_result(
    period: str, numbers: str, draw_date: str, session: Session = Depends(get_session)
):
    """新增開獎結果"""
    # 檢查是否已存在
    existing = session.exec(
        select(LotteryResult).where(LotteryResult.period == period)
    ).first()

    if existing:
        return ApiResponse(success=False, message=f"期別 {period} 已經存在")

    result = LotteryResult(period=period, numbers=numbers, draw_date=draw_date)
    session.add(result)
    session.commit()

    return ApiResponse(success=True, message="開獎結果已新增", data={"id": result.id})


# ============ 預測 API ============


class LotteryAnalyzer:
    """彩券分析器 - 多維度數據分析"""

    def __init__(self, results: List[LotteryResult]):
        self.results = results
        self.total_draws = len(results)

    def parse_numbers(self, numbers_str: str) -> List[int]:
        """解析號碼字符串"""
        return [int(n.strip()) for n in numbers_str.split(",")]

    def get_frequency_analysis(self, period: int = 30) -> dict:
        """
        頻率分析：統計指定期數內各號碼出現次數
        返回：{號碼：出現次數}
        """
        frequency = {}
        for r in self.results[:period]:
            nums = self.parse_numbers(r.numbers)
            for num in nums:
                frequency[num] = frequency.get(num, 0) + 1
        return frequency

    def get_omission_analysis(self) -> dict:
        """
        遺漏值分析：計算每個號碼連續未開出的期數
        返回：{號碼：遺漏期數}
        """
        omission = {num: 0 for num in range(1, 40)}

        for r in self.results:
            nums = self.parse_numbers(r.numbers)
            # 已開出的號碼重置遺漏值
            for num in nums:
                omission[num] = 0
            # 未開出的號碼遺漏值 +1
            for num in range(1, 40):
                if num not in nums:
                    omission[num] += 1

        return omission

    def get_odd_even_analysis(self, period: int = 30) -> dict:
        """
        奇偶分析：統計奇數和偶數的比例
        """
        odd_count = 0
        even_count = 0

        for r in self.results[:period]:
            nums = self.parse_numbers(r.numbers)
            for num in nums:
                if num % 2 == 0:
                    even_count += 1
                else:
                    odd_count += 1

        total = odd_count + even_count
        return {
            "odd": {"count": odd_count, "ratio": odd_count / total if total > 0 else 0},
            "even": {
                "count": even_count,
                "ratio": even_count / total if total > 0 else 0,
            },
        }

    def get_range_analysis(self, period: int = 30) -> dict:
        """
        大小號分析：將號碼分為小號 (1-19) 和大號 (20-39)
        """
        small_count = 0
        large_count = 0

        for r in self.results[:period]:
            nums = self.parse_numbers(r.numbers)
            for num in nums:
                if num <= 19:
                    small_count += 1
                else:
                    large_count += 1

        total = small_count + large_count
        return {
            "small": {
                "count": small_count,
                "ratio": small_count / total if total > 0 else 0,
            },
            "large": {
                "count": large_count,
                "ratio": large_count / total if total > 0 else 0,
            },
        }

    def get_tail_analysis(self, period: int = 30) -> dict:
        """
        同尾號分析：統計各尾數 (0-9) 的出現頻率
        """
        tail_freq = {i: 0 for i in range(10)}

        for r in self.results[:period]:
            nums = self.parse_numbers(r.numbers)
            for num in nums:
                tail = num % 10
                tail_freq[tail] += 1

        return tail_freq

    def get_consecutive_analysis(self, period: int = 30) -> dict:
        """
        連號分析：統計連號出現的模式
        """
        consecutive_pairs = {}

        for r in self.results[:period]:
            nums = sorted(self.parse_numbers(r.numbers))
            for i in range(len(nums) - 1):
                if nums[i + 1] - nums[i] == 1:
                    pair = (nums[i], nums[i + 1])
                    consecutive_pairs[pair] = consecutive_pairs.get(pair, 0) + 1

        return consecutive_pairs

    def calculate_composite_score(self) -> dict:
        """
        計算綜合評分：結合多個指標為每個號碼評分
        評分因素：
        - 頻率分數 (40%)：近期出現頻率
        - 遺漏分數 (25%)：遺漏值適中的號碼（太冷或太熱都不好）
        - 趨勢分數 (20%)：近期是否呈現上升趨勢
        - 尾號分數 (15%)：熱門尾數加分
        """
        # 短期頻率 (最近 10 期)
        short_freq = self.get_frequency_analysis(10)
        # 中期頻率 (最近 30 期)
        mid_freq = self.get_frequency_analysis(30)
        # 長期頻率 (全部)
        long_freq = self.get_frequency_analysis(self.total_draws)

        # 遺漏值
        omission = self.get_omission_analysis()

        # 尾號頻率
        tail_freq = self.get_tail_analysis(30)

        # 計算各指標的最大值用於歸一化
        max_short = max(short_freq.values()) if short_freq else 1
        max_mid = max(mid_freq.values()) if mid_freq else 1

        scores = {}

        for num in range(1, 40):
            # 頻率分數 (40%): 綜合短中長期
            short_score = (
                (short_freq.get(num, 0) / max_short) * 100 if max_short > 0 else 0
            )
            mid_score = (mid_freq.get(num, 0) / max_mid) * 100 if max_mid > 0 else 0
            long_score = (
                (long_freq.get(num, 0) / max(long_freq.values())) * 100
                if long_freq
                else 0
            )

            freq_score = short_score * 0.5 + mid_score * 0.3 + long_score * 0.2

            # 遺漏分數 (25%): 遺漏值在 3-10 之間最佳
            omit = omission.get(num, 0)
            if 3 <= omit <= 10:
                omit_score = 100 - abs(omit - 6.5) * 5  # 以 6.5 為中心
            elif omit < 3:
                omit_score = 80 - omit * 10  # 太熱稍微降分
            else:
                omit_score = max(20, 100 - omit * 3)  # 太冷大幅降分但仍保留機會

            # 趨勢分數 (20%): 比較短期與中期頻率
            short_rate = short_freq.get(num, 0) / 10 if short_freq else 0
            mid_rate = mid_freq.get(num, 0) / 30 if mid_freq else 0
            if short_rate > mid_rate * 1.5:
                trend_score = 100  # 上升趨勢
            elif short_rate < mid_rate * 0.5:
                trend_score = 40  # 下降趨勢
            else:
                trend_score = 70  # 穩定

            # 尾號分數 (15%)
            tail = num % 10
            max_tail = max(tail_freq.values()) if tail_freq else 1
            tail_score = (
                (tail_freq.get(tail, 0) / max_tail) * 100 if max_tail > 0 else 0
            )

            # 綜合評分
            composite = (
                freq_score * 0.40
                + omit_score * 0.25
                + trend_score * 0.20
                + tail_score * 0.15
            )

            scores[num] = round(composite, 2)

        return scores


@app.get("/api/prediction", response_model=ApiResponse)
def get_prediction(session: Session = Depends(get_session)):
    """
    取得預測號碼 - 簡化版

    選號策略：
    1. 最近30期出現次數 >= 4 的號碼
    2. 減掉最近三期開出的號碼
    3. 隨機選擇 5 個號碼（不加權）
    """
    import random

    results = session.exec(
        select(LotteryResult).order_by(LotteryResult.id.desc()).limit(30)
    ).all()

    if not results:
        return ApiResponse(success=False, message="尚無足夠資料進行預測")

    analyzer = LotteryAnalyzer(results)

    # 最近30期出現次數
    frequency = analyzer.get_frequency_analysis(30)

    # 熱門號碼（出現次數 >= 4）
    hot_numbers = [num for num, count in frequency.items() if count >= 4]

    # 取得最近三期開獎號碼（用於排除）
    recent_3_results = session.exec(
        select(LotteryResult).order_by(LotteryResult.id.desc()).limit(3)
    ).all()

    recent_3_numbers = set()
    for r in recent_3_results:
        nums = analyzer.parse_numbers(r.numbers)
        recent_3_numbers.update(nums)

    # 過濾後可供預測的號碼
    filtered_numbers = [n for n in hot_numbers if n not in recent_3_numbers]

    # 隨機選擇 5 個號碼
    def generate_prediction(exclude_set: set = None) -> List[int]:
        if exclude_set is None:
            exclude_set = set()

        available = [n for n in filtered_numbers if n not in exclude_set]
        random.shuffle(available)
        return sorted(available[:5])

    # 產生第一組預測
    prediction_set1 = generate_prediction(recent_3_numbers)

    # 產生第二組預測
    prediction_set2 = generate_prediction(set(prediction_set1) | recent_3_numbers)

    # 準備詳細分析資料
    frequency_analysis = {
        str(num): count
        for num, count in sorted(frequency.items(), key=lambda x: x[1], reverse=True)
    }

    data = {
        "numbers": ", ".join([str(n).zfill(2) for n in prediction_set1]),
        "numbers2": ", ".join([str(n).zfill(2) for n in prediction_set2]),
        "analysis": {
            "hot_numbers": sorted(hot_numbers),
            "recent_3_numbers": sorted(recent_3_numbers),
            "filtered_numbers": sorted(filtered_numbers),
            "frequency": frequency_analysis,
        },
    }

    return ApiResponse(success=True, data=data)


@app.get("/api/prediction/ml", response_model=ApiResponse)
def get_ml_prediction(session: Session = Depends(get_session)):
    """
    ML 預測號碼 - 使用加權隨機選號策略

    策略：
    1. 分析最近50期號碼出現頻率
    2. 計算每個號碼的權重（出現次數 + 遺漏期數）
    3. 使用加權隨機選擇 5 個號碼
    4. 排除最近3期已開出的號碼
    """
    import random
    import math

    results = session.exec(
        select(LotteryResult).order_by(LotteryResult.id.desc()).limit(50)
    ).all()

    if not results:
        return ApiResponse(success=False, message="尚無足夠資料進行預測")

    analyzer = LotteryAnalyzer(results)

    frequency = analyzer.get_frequency_analysis(50)

    recent_3_results = session.exec(
        select(LotteryResult).order_by(LotteryResult.id.desc()).limit(3)
    ).all()

    recent_3_numbers = set()
    for r in recent_3_results:
        nums = analyzer.parse_numbers(r.numbers)
        recent_3_numbers.update(nums)

    missing_days = {}
    all_numbers = set(range(1, 40))
    for num in all_numbers:
        last_seen = None
        for i, r in enumerate(results):
            nums = analyzer.parse_numbers(r.numbers)
            if num in nums:
                last_seen = i
                break
        missing_days[num] = last_seen if last_seen is not None else 50

    def calculate_weight(freq: int, missing: int) -> float:
        freq_weight = freq * 2
        missing_weight = math.log(missing + 1) * 1.5
        return freq_weight + missing_weight

    weights = {}
    for num in range(1, 40):
        freq = frequency.get(num, 0)
        miss = missing_days.get(num, 50)
        if freq > 0:
            weights[num] = calculate_weight(freq, miss)
        else:
            weights[num] = calculate_weight(0, miss) * 0.5

    total_weight = sum(weights.values())
    probabilities = {num: w / total_weight for num, w in weights.items()}

    numbers_list = list(probabilities.keys())
    probs_list = list(probabilities.values())

    nums_pool1 = list(numbers_list)
    probs_pool1 = list(probs_list)

    def select_numbers(pool: list = None, pool_weights: list = None) -> List[int]:
        if pool is None:
            pool = nums_pool1
            pool_weights = probs_pool1
        selected = set(random.choices(pool, weights=pool_weights, k=5))
        while len(selected) < 5:
            remaining = [n for n in pool if n not in selected]
            if remaining:
                selected.add(random.choice(remaining))
            else:
                break
        return sorted(selected)

    prediction_set1 = select_numbers()

    prediction_set2 = select_numbers()

    frequency_analysis = {
        str(num): count
        for num, count in sorted(frequency.items(), key=lambda x: x[1], reverse=True)
    }

    data = {
        "numbers": ", ".join([str(n).zfill(2) for n in prediction_set1]),
        "numbers2": ", ".join([str(n).zfill(2) for n in prediction_set2]),
        "analysis": {
            "hot_numbers": [n for n in range(1, 40) if frequency.get(n, 0) >= 4],
            "recent_3_numbers": sorted(recent_3_numbers),
            "filtered_numbers": [n for n in range(1, 40) if n not in recent_3_numbers],
            "frequency": frequency_analysis,
        },
    }

    return ApiResponse(success=True, data=data)


def generate_prediction_sets(
    frequent_numbers: List[int], frequency: dict, sorted_simulation: List[tuple]
) -> List[str]:
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
        max_sim = (
            max(sorted_simulation, key=lambda x: x[1])[1] if sorted_simulation else 1
        )

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
                    odd_pool = [
                        n
                        for n in range(1, 40)
                        if n % 2 == 1 and n not in final_selection
                    ]
                    if odd_pool:
                        final_selection.append(random.choice(odd_pool[:10]))
            elif odd_count > 3:
                odd_nums = [n for n in final_selection if n % 2 == 1]
                if odd_nums:
                    final_selection.remove(random.choice(odd_nums))
                    even_pool = [
                        n
                        for n in range(1, 40)
                        if n % 2 == 0 and n not in final_selection
                    ]
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
                odd_pool = [
                    n for n in range(1, 40) if n % 2 == 1 and n not in final_selection
                ]
                if odd_pool:
                    final_selection.append(random.choice(odd_pool[:10]))
        elif odd_count > 3:
            # 太多奇數，替換一個奇數為偶數
            odd_nums = [n for n in final_selection if n % 2 == 1]
            if odd_nums:
                final_selection.remove(random.choice(odd_nums))
                # 加入一個偶數
                even_pool = [
                    n for n in range(1, 40) if n % 2 == 0 and n not in final_selection
                ]
                if even_pool:
                    final_selection.append(random.choice(even_pool[:10]))

    result = sorted(set(final_selection))[:5]
    return ", ".join([str(n).zfill(2) for n in result])


@app.post("/api/prediction", response_model=ApiResponse)
def save_prediction(
    period: str,
    numbers: str,
    numbers2: str = "",
    session: Session = Depends(get_session),
):
    """儲存預測"""
    try:
        prediction = Prediction(
            period=period, numbers=numbers, numbers2=numbers2 if numbers2 else None
        )
        session.add(prediction)
        session.commit()

        return ApiResponse(
            success=True, message="預測已儲存", data={"id": prediction.id}
        )
    except Exception as e:
        session.rollback()
        # 嘗試只儲存 numbers
        try:
            prediction = Prediction(period=period, numbers=numbers)
            session.add(prediction)
            session.commit()
            return ApiResponse(
                success=True, message="預測已儲存(第一組)", data={"id": prediction.id}
            )
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
