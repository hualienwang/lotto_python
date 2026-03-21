<template>
  <div>
    <!-- 本期預測區塊 -->
    <div class="card">
      <h2>🔮 本期預測</h2>
      <div class="prediction-box">
        <p>根據最近30期開獎號碼中出現次數大於等於4次的號碼，隨機模擬1000次開獎後統計分析</p>
        
        <template v-if="store.loading">
          <div class="loading">載入中...</div>
        </template>
        <template v-else-if="!store.prediction">
          <div class="loading">
            <p>請點擊下方「開始預測」按鈕產生預測號碼</p>
            <button class="btn" @click="getNewPrediction">開始預測</button>
          </div>
        </template>
        <template v-else-if="predictionNumbers.length > 0">
          <div class="prediction-numbers">
            <!-- 兩組預測號碼 -->
            <div class="prediction-sets">
              <div class="prediction-set">
                <div class="set-label">🏆 預測號碼 A</div>
                <div class="numbers">
                  <span 
                    v-for="num in predictionNumbers" 
                    :key="'a-' + num" 
                    class="number number-a"
                  >
                    {{ num }}
                  </span>
                </div>
              </div>
              <div class="prediction-set">
                <div class="set-label">🏆 預測號碼 B</div>
                <div class="numbers">
                  <span 
                    v-for="num in predictionNumbers2" 
                    :key="'b-' + num" 
                    class="number number-b"
                  >
                    {{ num }}
                  </span>
                </div>
              </div>
            </div>
            
            <div class="button-group">
              <button class="btn" @click="getNewPrediction">重新預測</button>
              <button class="btn btn-secondary" @click="saveCurrentPrediction">儲存預測</button>
            </div>
            <div v-if="message" :class="messageClass">{{ message }}</div>
          </div>
        </template>
        <template v-else>
          <div class="loading">載入預測中...</div>
        </template>
      </div>
    </div>

    <!-- 分析結果區塊 -->
    <div class="card" v-if="store.prediction?.analysis">
      <h2>📊 模擬分析結果 (1000次)</h2>
      <div class="analysis-box">
        <!-- 出現次數 > 4 的號碼 -->
        <div class="frequent-numbers">
          <h3>🔥 最近30期出現次數 >= 4 的號碼</h3>
          <div class="numbers">
            <span 
              v-for="num in frequentNumbers" 
              :key="'freq-' + num" 
              class="number number-highlight"
            >
              {{ String(num).padStart(2, '0') }}
              <span class="count">({{ getFrequencyCount(num) }})</span>
            </span>
          </div>
        </div>
        
        <!-- 模擬1000次結果 -->
        <div class="simulation-results">
          <h3>📈 模擬1000次開獎號碼出現次數排序</h3>
          <!-- 統計數值 -->
          <div class="simulation-stats">
            <div class="stat-item">
              <span class="stat-label">眾數：</span>
              <span class="stat-value">{{ simulationStats.mode }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">中位數：</span>
              <span class="stat-value">{{ simulationStats.median }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">平均數：</span>
              <span class="stat-value">{{ simulationStats.mean }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">標準差：</span>
              <span class="stat-value">{{ simulationStats.stdDev }}</span>
            </div>
          </div>
          <div class="frequency-chart">
            <div 
              v-for="item in sortedSimulation" 
              :key="'sim-' + item.num" 
              class="freq-bar-container"
            >
              <span class="freq-label">{{ String(item.num).padStart(2, '0') }}</span>
              <div class="freq-bar-wrapper">
                <div 
                  class="freq-bar" 
                  :style="{ width: (item.count / maxSimulationCount * 100) + '%' }"
                ></div>
              </div>
              <span class="freq-count">{{ item.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useLotteryStore } from '../stores/lottery'

const store = useLotteryStore()
const message = ref('')
const messageClass = ref('')

// 第一組預測號碼
const predictionNumbers = computed(() => {
  if (!store.prediction?.numbers) return []
  return store.prediction.numbers.split(',').map(n => n.trim())
})

// 第二組預測號碼
const predictionNumbers2 = computed(() => {
  if (!store.prediction?.numbers2) return []
  return store.prediction.numbers2.split(',').map(n => n.trim())
})

// 頻繁號碼（出現次數 >= 4）
const frequentNumbers = computed(() => {
  return store.prediction?.analysis?.frequent_numbers || []
})

// 取得號碼出現次數
const getFrequencyCount = (num) => {
  return store.prediction?.analysis?.frequency?.[num] || 0
}

// 模擬1000次結果排序（只顯示有出現的號碼）
const sortedSimulation = computed(() => {
  const sim = store.prediction?.analysis?.simulation_1000 || {}
  const result = []
  for (const [num, count] of Object.entries(sim)) {
    if (count > 0) {  // 過濾掉未出現的號碼
      result.push({ num: parseInt(num), count })
    }
  }
  return result.sort((a, b) => b.count - a.count)
})

// 模擬1000次統計數值
const simulationStats = computed(() => {
  const sim = store.prediction?.analysis?.simulation_1000 || {}
  const counts = Object.values(sim)
  
  if (counts.length === 0) {
    return { mode: '-', median: '-', mean: '-', stdDev: '-' }
  }
  
  // 平均數
  const sum = counts.reduce((a, b) => a + b, 0)
  const mean = sum / counts.length
  
  // 中位數
  const sorted = [...counts].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  const median = sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
  
  // 標準差
  const variance = counts.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / counts.length
  const stdDev = Math.sqrt(variance)
  
  // 眾數
  const freqMap = {}
  let maxFreq = 0
  counts.forEach(c => {
    freqMap[c] = (freqMap[c] || 0) + 1
    if (freqMap[c] > maxFreq) maxFreq = freqMap[c]
  })
  const modeCounts = Object.keys(freqMap).filter(k => freqMap[k] === maxFreq)
  const mode = modeCounts.join(', ')
  
  return {
    mode: `出現${modeCounts[0]}次的號碼有${modeCounts.length}個`,
    median: median.toFixed(2),
    mean: mean.toFixed(2),
    stdDev: stdDev.toFixed(2)
  }
})

// 最大模擬次數（用於計算百分比）
const maxSimulationCount = computed(() => {
  if (sortedSimulation.value.length === 0) return 1
  return Math.max(...sortedSimulation.value.map(s => s.count))
})

const getNewPrediction = () => {
  message.value = ''
  store.fetchPrediction()
}

const saveCurrentPrediction = async () => {
  if (!store.prediction?.numbers) return
  
  try {
    const period = store.latestResult ? String(Number(store.latestResult.period) + 1) : '000000'
    await store.savePrediction({
      period,
      numbers: store.prediction.numbers,
      numbers2: store.prediction.numbers2 || ''
    })
    message.value = '預測已儲存成功！'
    messageClass.value = 'success'
  } catch (err) {
    message.value = '儲存失敗：' + err.message
    messageClass.value = 'error'
  }
}

onMounted(() => {
  // 不自動載入預測，等用戶點擊重新預測按鈕
  store.fetchLatestResult()
})
</script>

<style scoped>
.prediction-sets {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.prediction-set {
  flex: 1;
  min-width: 250px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
}

.set-label {
  text-align: center;
  font-size: 1.1rem;
  font-weight: bold;
  margin-bottom: 15px;
  color: #ffd700;
}

.number-a {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.number-b {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.button-group {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 15px;
}

.analysis-box {
  padding: 10px;
}

.frequent-numbers {
  margin-bottom: 25px;
}

.frequent-numbers h3,
.simulation-results h3 {
  font-size: 1rem;
  margin-bottom: 15px;
  color: #ffd700;
}

.number-highlight {
  background: linear-gradient(135deg, #ffd700 0%, #ffaa00 100%);
  color: #333;
  font-weight: bold;
}

.number-highlight .count {
  font-size: 0.75rem;
  color: #555;
}

.simulation-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 20px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.stat-label {
  color: #aaa;
  font-size: 0.9rem;
}

.stat-value {
  color: #ffd700;
  font-weight: bold;
  font-size: 0.9rem;
}

.frequency-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.freq-bar-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.freq-label {
  width: 30px;
  font-weight: bold;
  text-align: center;
}

.freq-bar-wrapper {
  flex: 1;
  height: 20px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  overflow: hidden;
}

.freq-bar {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  transition: width 0.3s ease;
}

.freq-count {
  width: 40px;
  text-align: right;
  font-size: 0.9rem;
  color: #aaa;
}
</style>
