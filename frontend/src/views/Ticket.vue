<template>
  <div>
    <div class="card">
      <h2>🎫 號碼選擇</h2>
      <p>最近30期開獎號碼中出現次數 >= 4 的號碼以不同顏色標示</p>
      
      <template v-if="store.loading">
        <div class="loading">載入中...</div>
      </template>
      <template v-else>
        <!-- 獎號區 -->
        <div class="ticket-section">
          <h3>📊 最近30期開獎號碼統計 (上)</h3>
          <div class="number-grid">
            <div 
              v-for="num in 39" 
              :key="'freq-' + num" 
              :class="['number-cell', getNumberClass(num), { 'is-latest': isLatestNumber(num) }]"
            >
              <span class="number-text">{{ String(num).padStart(2, '0') }}</span>
              <span v-if="isLatestNumber(num)" class="checkmark">✓</span>
              <span class="count">({{ getFrequencyCount(num) }})</span>
            </div>
          </div>
        </div>

        <!-- 獎號區2 -->
        <div class="ticket-section">
          <h3>📊 最近30期開獎號碼統計 (下) - 點擊選擇號碼</h3>
          <div class="number-grid">
            <div 
              v-for="num in 39" 
              :key="'freq2-' + num" 
              :class="['number-cell', { 'is-latest': isLatestNumber(num), 'is-selected': isSelected(num) }]"
              @click="toggleNumber(num)"
            >
              <span class="number-text">{{ String(num).padStart(2, '0') }}</span>
              <span v-if="isLatestNumber(num)" class="checkmark">✓</span>
              <span class="count">({{ getFrequencyCount(num) }})</span>
            </div>
          </div>
        </div>

        <!-- 過濾後可供預測的號碼 -->
        <div class="ticket-section" v-if="store.prediction?.analysis?.filtered_numbers">
          <h3>✅ 過濾後可供預測的號碼</h3>
          <div class="number-grid">
            <div 
              v-for="num in filteredNumbers" 
              :key="'filtered-' + num" 
              class="number-cell filtered-number"
            >
              {{ String(num).padStart(2, '0') }}
            </div>
          </div>
        </div>

        <!-- 預測區 -->
        <div class="ticket-section" v-if="store.prediction?.numbers">
          <h3>🔮 預測號碼</h3>
          <!-- 預測號碼 A -->
          <div class="prediction-ticket">
            <div class="ticket-label">🏆 預測號碼 A</div>
            <div class="number-grid">
              <div 
                v-for="num in predictionNumbers" 
                :key="'pred-a-' + num" 
                class="number-cell prediction-a"
              >
                {{ num }}
              </div>
            </div>
          </div>
          <!-- 預測號碼 B -->
          <div class="prediction-ticket" v-if="predictionNumbers2.length > 0">
            <div class="ticket-label">🏆 預測號碼 B</div>
            <div class="number-grid">
              <div 
                v-for="num in predictionNumbers2" 
                :key="'pred-b-' + num" 
                class="number-cell prediction-b"
              >
                {{ num }}
              </div>
            </div>
          </div>
        </div>

        <div class="button-group" v-if="!store.prediction?.numbers">
          <button class="btn" @click="getNewPrediction">開始預測</button>
        </div>
        <div class="button-group" v-else>
          <button class="btn" @click="getNewPrediction">重新預測</button>
          <button class="btn btn-secondary" @click="saveCurrentPrediction">儲存預測</button>
        </div>
        <div v-if="message" :class="messageClass">{{ message }}</div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useLotteryStore } from '../stores/lottery'

const store = useLotteryStore()
const message = ref('')
const messageClass = ref('')

// 選中的號碼
const selectedNumbers = ref([])

// 檢查號碼是否被選中
const isSelected = (num) => {
  return selectedNumbers.value.includes(num)
}

// 切換號碼選中狀態
const toggleNumber = (num) => {
  const index = selectedNumbers.value.indexOf(num)
  if (index === -1) {
    selectedNumbers.value.push(num)
  } else {
    selectedNumbers.value.splice(index, 1)
  }
}

// 取得號碼出現次數
const getFrequencyCount = (num) => {
  return store.prediction?.analysis?.frequency?.[num] || 0
}

// 取得最新開獎號碼
const latestNumbers = computed(() => {
  if (!store.latestResult?.numbers) return []
  return store.latestResult.numbers.split(',').map(n => n.trim())
})

// 最近3期開獎號碼
const latest3Results = computed(() => {
  const results = store.results || []
  return results.slice(0, 3)
})

// 格式化號碼為陣列
const formatNumbers = (numbers) => {
  if (!numbers) return []
  return numbers.split(',').map(n => n.trim())
}

// 檢查是否為最新開獎號碼
const isLatestNumber = (num) => {
  const numStr = String(num).padStart(2, '0')
  return latestNumbers.value.includes(numStr)
}

// 取得號碼样式
const getNumberClass = (num) => {
  const count = getFrequencyCount(num)
  if (count >= 6) return 'freq-6'
  if (count >= 5) return 'freq-5'
  if (count >= 4) return 'freq-4'
  return ''
}

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

// 過濾後可供預測的號碼
const filteredNumbers = computed(() => {
  return store.prediction?.analysis?.filtered_numbers || []
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
  store.fetchLatestResult()
  store.fetchResults()
})
</script>

<style scoped>
.ticket-section {
  margin-bottom: 25px;
}

.ticket-section h3 {
  font-size: 1rem;
  margin-bottom: 15px;
  color: #ffd700;
}

.number-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 8px;
}

.number-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 5px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  font-weight: bold;
  min-height: 50px;
  position: relative;
}

.number-cell.is-latest {
  border: 3px solid #ffd700;
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
}

.number-text {
  line-height: 1;
}

.checkmark {
  position: absolute;
  top: 2px;
  right: 2px;
  font-size: 0.7rem;
  font-weight: bold;
}

.number-cell.freq-4 .checkmark {
  color: #14532d;
}

.number-cell.freq-5 .checkmark {
  color: #78350f;
}

.number-cell.freq-6 .checkmark {
  color: #fef2f2;
}

.number-cell:not(.freq-4):not(.freq-5):not(.freq-6) .checkmark {
  color: #ffd700;
}

.number-cell .count {
  font-size: 0.7rem;
  font-weight: normal;
  margin-top: 2px;
}

/* 出現次數顏色標示 */
.number-cell.freq-4 {
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
  color: #000;
}

.number-cell.freq-4 .count {
  color: #14532d;
}

.number-cell.freq-5 {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #000;
}

.number-cell.freq-5 .count {
  color: #78350f;
}

.number-cell.freq-6 {
  background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
  color: #fff;
}

.number-cell.freq-6 .count {
  color: #fef2f2;
}

/* 過濾後可供預測的號碼樣式 */
.number-cell.filtered-number {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
  border: 2px solid #34d399;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}

/* 選中號碼樣式 */
.number-cell.is-selected {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%) !important;
  color: #000;
  cursor: pointer;
  transform: scale(1.05);
  transition: all 0.2s ease;
}

.number-cell.is-selected .count {
  color: #78350f;
}

.number-cell.is-selected .checkmark {
  color: #78350f;
}

/* 預測號碼樣式 */
.prediction-ticket {
  margin-bottom: 15px;
}

.ticket-label {
  text-align: center;
  font-size: 0.9rem;
  font-weight: bold;
  margin-bottom: 10px;
  color: #ffd700;
}

.number-cell.prediction-a {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.number-cell.prediction-b {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
}

.button-group {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

/* 最近3期開獎號碼 */
.latest-results {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}

.result-period {
  font-weight: bold;
  color: #ffd700;
  min-width: 80px;
  font-size: 14px;
}

.result-numbers {
  display: flex;
  gap: 8px;
}

.number-ball {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-size: 14px;
  font-weight: bold;
  background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
  color: white;
}
</style>
