<template>
  <div>
    <!-- 本期預測區塊 -->
    <div class="card">
      <h2>🔮 本期預測</h2>
      <div class="prediction-box">
        <p>根據最近30期開獎號碼中出現次數大於等於4次的號碼（熱門號碼），減去最近三期開獎號碼後，隨機選擇5個號碼進行預測（不加權）</p>
        
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

    <!-- ML 預測區塊 -->
    <div class="card">
      <h2>🤖 ML 預測</h2>
      <div class="prediction-box">
        <p>使用加權隨機選號策略，分析最近50期號碼出現頻率與遺漏期數，計算權重後隨機選擇5個號碼</p>
        
        <template v-if="store.loading">
          <div class="loading">載入中...</div>
        </template>
        <template v-else-if="!store.mlPrediction">
          <div class="loading">
            <p>請點擊下方「開始 ML 預測」按鈕產生預測號碼</p>
            <button class="btn btn-ml" @click="getNewMLPrediction">開始 ML 預測</button>
          </div>
        </template>
        <template v-else-if="store.mlPrediction && mlPredictionNumbers.length > 0">
          <div class="prediction-numbers">
            <div class="prediction-sets">
              <div class="prediction-set">
                <div class="set-label">🤖 ML 預測號碼 A</div>
                <div class="numbers">
                  <span 
                    v-for="num in mlPredictionNumbers" 
                    :key="'ml-a-' + num" 
                    class="number number-ml-a"
                  >
                    {{ num }}
                  </span>
                </div>
              </div>
              <div class="prediction-set">
                <div class="set-label">🤖 ML 預測號碼 B</div>
                <div class="numbers">
                  <span 
                    v-for="num in mlPredictionNumbers2" 
                    :key="'ml-b-' + num" 
                    class="number number-ml-b"
                  >
                    {{ num }}
                  </span>
                </div>
              </div>
            </div>
            
            <div class="button-group">
              <button class="btn btn-ml" @click="getNewMLPrediction">重新 ML 預測</button>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="loading">載入 ML 預測中...</div>
        </template>
      </div>
    </div>

    <!-- 分析結果區塊 -->
    <div class="card" v-if="store.prediction?.analysis">
      <h2>📊 預測分析</h2>
      <div class="analysis-box">
        <!-- 熱門號碼 -->
        <div class="frequent-numbers">
          <h3>🔥 最近30期出現次數 >= 4 的號碼（熱門號碼）</h3>
          <div class="numbers">
            <span 
              v-for="num in hotNumbers" 
              :key="'hot-' + num" 
              class="number number-highlight"
            >
              {{ String(num).padStart(2, '0') }}
              <span class="count">({{ getFrequencyCount(num) }})</span>
            </span>
          </div>
        </div>
        
        <!-- 最近三期號碼 -->
        <div class="recent-numbers">
          <h3>📅 最近三期開獎號碼（已排除）</h3>
          <div class="numbers">
            <span 
              v-for="num in recent3Numbers" 
              :key="'recent-' + num" 
              class="number number-recent"
            >
              {{ String(num).padStart(2, '0') }}
            </span>
          </div>
        </div>
        
        <!-- 過濾後可供預測的號碼 -->
        <div class="filtered-numbers">
          <h3>✅ 過濾後可供預測的號碼</h3>
          <div class="numbers">
            <span 
              v-for="num in filteredNumbers" 
              :key="'filtered-' + num" 
              class="number number-filtered"
            >
              {{ String(num).padStart(2, '0') }}
            </span>
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

// 熱門號碼（出現次數 >= 4）
const hotNumbers = computed(() => {
  return store.prediction?.analysis?.hot_numbers || []
})

// 最近三期開獎號碼
const recent3Numbers = computed(() => {
  return store.prediction?.analysis?.recent_3_numbers || []
})

// 過濾後可供預測的號碼
const filteredNumbers = computed(() => {
  return store.prediction?.analysis?.filtered_numbers || []
})

// ML 預測號碼
const mlPredictionNumbers = computed(() => {
  if (!store.mlPrediction?.numbers) return []
  return store.mlPrediction.numbers.split(',').map(n => n.trim())
})

const mlPredictionNumbers2 = computed(() => {
  if (!store.mlPrediction?.numbers2) return []
  return store.mlPrediction.numbers2.split(',').map(n => n.trim())
})

// 取得號碼出現次數
const getFrequencyCount = (num) => {
  return store.prediction?.analysis?.frequency?.[num] || 0
}

const getNewPrediction = () => {
  message.value = ''
  store.fetchPrediction()
}

const getNewMLPrediction = () => {
  message.value = ''
  store.fetchMLPrediction()
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

.frequent-numbers,
.recent-numbers,
.filtered-numbers {
  margin-bottom: 25px;
}

.frequent-numbers h3,
.recent-numbers h3,
.filtered-numbers h3 {
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

.number-recent {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%);
}

.number-filtered {
  background: linear-gradient(135deg, #51cf66 0%, #40c057 100%);
}

.number-ml-a {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.number-ml-b {
  background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
}

.btn-ml {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.btn-ml:hover {
  background: linear-gradient(135deg, #0d8a76 0%, #2fd36a 100%);
}
</style>
