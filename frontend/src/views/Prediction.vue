<template>
  <div>
    <!-- 天干地支預測區塊 -->
    <div class="card">
      <h2>🧧 天干地支預測</h2>
      <div class="prediction-box">
        <p>根據傳統農曆天干地支計算最佳預測時間與號碼</p>
        
        <div v-if="store.loading" class="loading">載入中...</div>
        <div v-else-if="tianganNumbers.length > 0" class="prediction-numbers">
          <!-- 天干地支資訊 -->
          <div class="tiangan-info">
            <div class="tiangan-badge">
              <span class="tg">{{ tiangan }}</span>
              <span class="dz">{{ dizhi }}</span>
              <span class="year">年</span>
            </div>
            <div class="prediction-time">
              預測日期: {{ predictionDate }} {{ predictionTime }}
            </div>
            <div class="lucky-hours">
              吉時: 
              <span v-for="(hour, idx) in luckyHours" :key="hour" class="lucky-hour">
                {{ hour }}:00<span v-if="idx < luckyHours.length - 1">, </span>
              </span>
            </div>
          </div>
          
          <!-- 預測號碼 -->
          <div class="numbers">
            <span 
              v-for="num in tianganNumbers" 
              :key="num" 
              class="number"
            >
              {{ num }}
            </span>
          </div>
          
          <!-- 吉時號碼參考 -->
          <div v-if="luckyReferenceNumbers.length > 0" class="lucky-reference">
            <div class="lucky-ref-label">⭐ 當日吉時號碼參考：</div>
            <div class="numbers">
              <span 
                v-for="num in luckyReferenceNumbers" 
                :key="num" 
                class="number number-lucky"
              >
                {{ num }}
              </span>
            </div>
          </div>
          
          <button class="btn" @click="getNewTianganPrediction">重新預測</button>
          <button class="btn btn-secondary" @click="saveTianganPrediction">儲存預測</button>
          <div v-if="tianganMessage" :class="tianganMessageClass">{{ tianganMessage }}</div>
        </div>
        <div v-else class="loading">載入天干地支預測中...</div>
      </div>
    </div>

    <!-- 原有的大數據分析預測區塊 -->
    <div class="card">
      <h2>🔮 本期預測</h2>
      <div class="prediction-box">
        <p>基於大數據分析，計算出最有可能開出的號碼</p>
        
        <div v-if="store.loading" class="loading">載入中...</div>
        <div v-else-if="predictionNumbers.length > 0" class="prediction-numbers">
          <div class="numbers">
            <span 
              v-for="num in predictionNumbers" 
              :key="num" 
              class="number"
            >
              {{ num }}
            </span>
          </div>
          <button class="btn" @click="getNewPrediction">重新預測</button>
          <button class="btn btn-secondary" @click="saveCurrentPrediction">儲存預測</button>
          <div v-if="message" :class="messageClass">{{ message }}</div>
        </div>
        <div v-else class="loading">載入預測中...</div>
      </div>
    </div>

    <div class="card">
      <h2>🔥 熱門號碼 TOP 10</h2>
      <div v-if="hotNumbers.length > 0" class="hot-numbers">
        <span 
          v-for="num in hotNumbers" 
          :key="num" 
          class="hot-number"
        >
          {{ String(num).padStart(2, '0') }}
          <span class="count">({{ frequencyData[num] }})</span>
        </span>
      </div>
      <div v-else class="loading">載入中...</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useLotteryStore } from '../stores/lottery'

const store = useLotteryStore()
const message = ref('')
const messageClass = ref('')
const tianganMessage = ref('')
const tianganMessageClass = ref('')

// 天干地支預測
const tianganPrediction = computed(() => store.tianganPrediction || {})

const tianganNumbers = computed(() => {
  const pred = tianganPrediction.value
  if (!pred.numbers) return []
  return pred.numbers.split(',').map(n => n.trim())
})

const luckyReferenceNumbers = computed(() => {
  const pred = tianganPrediction.value
  if (!pred.lucky_reference_numbers) return []
  return pred.lucky_reference_numbers.split(',').map(n => n.trim())
})

const tiangan = computed(() => tianganPrediction.value.tiangan || '')
const dizhi = computed(() => tianganPrediction.value.dizhi || '')
const predictionDate = computed(() => tianganPrediction.value.prediction_date || '')
const predictionTime = computed(() => tianganPrediction.value.prediction_time || '')
const luckyHours = computed(() => tianganPrediction.value.lucky_hours || [])

const getNewTianganPrediction = () => {
  tianganMessage.value = ''
  store.fetchTianganPrediction()
}

const saveTianganPrediction = async () => {
  const pred = tianganPrediction.value
  if (!pred.numbers) return
  
  try {
    const period = store.latestResult ? String(Number(store.latestResult.period) + 1) : '000000'
    await store.savePrediction({
      period,
      numbers: pred.numbers
    })
    tianganMessage.value = '天干地支預測已儲存成功！'
    tianganMessageClass.value = 'success'
  } catch (err) {
    tianganMessage.value = '儲存失敗：' + err.message
    tianganMessageClass.value = 'error'
  }
}

// 大數據分析預測
const predictionNumbers = computed(() => {
  if (!store.prediction?.numbers) return []
  return store.prediction.numbers.split(',').map(n => n.trim())
})

const hotNumbers = computed(() => {
  return store.prediction?.analysis?.hot_numbers || []
})

const frequencyData = computed(() => {
  return store.prediction?.analysis?.frequency || {}
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
      numbers: store.prediction.numbers
    })
    message.value = '預測已儲存成功！'
    messageClass.value = 'success'
  } catch (err) {
    message.value = '儲存失敗：' + err.message
    messageClass.value = 'error'
  }
}

onMounted(() => {
  store.fetchPrediction()
  store.fetchLatestResult()
  store.fetchTianganPrediction()
})
</script>

<style scoped>
.tiangan-info {
  margin-bottom: 20px;
  padding: 15px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  color: white;
}

.tiangan-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  margin-bottom: 10px;
}

.tiangan-badge .tg,
.tiangan-badge .dz {
  font-size: 2.5rem;
  font-weight: bold;
}

.tiangan-badge .year {
  font-size: 1.5rem;
  margin-left: 5px;
}

.prediction-time,
.lucky-hours {
  text-align: center;
  margin-top: 8px;
  font-size: 0.95rem;
}

.lucky-hour {
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 8px;
  border-radius: 4px;
  margin: 0 2px;
}

.lucky-reference {
  margin-top: 20px;
  padding: 15px;
  background: rgba(255, 215, 0, 0.1);
  border-radius: 10px;
  border: 1px solid rgba(255, 215, 0, 0.3);
}

.lucky-ref-label {
  text-align: center;
  font-weight: bold;
  margin-bottom: 10px;
  color: #ffd700;
}

.number-lucky {
  background: linear-gradient(135deg, #ffd700 0%, #ffaa00 100%);
  color: #333;
}
</style>
