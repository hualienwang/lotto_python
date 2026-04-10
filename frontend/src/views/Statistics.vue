<template>
  <div>
    <div class="card">
      <h2>🎯 號碼出現頻率</h2>
      
      <div v-if="hasFrequency" class="frequency-chart">
        <div class="frequency-grid">
          <div 
            v-for="n in 39" 
            :key="n" 
            class="frequency-item"
          >
            <span class="freq-count">{{ frequencyData[n] }}</span>
            <div class="freq-bar-container" v-if="frequencyData[n] > 0">
              <div 
                class="freq-bar" 
                :style="{ height: getBarHeight(frequencyData[n]) + 'px' }"
              ></div>
            </div>
            <div class="freq-bar-container" v-else style="height: 60px;"></div>
            <span class="freq-number">{{ String(n).padStart(2, '0') }}</span>
          </div>
        </div>
      </div>
      <div v-else class="loading">載入中...</div>
    </div>

    <div class="card">
      <h2>🔥 號碼分類</h2>
      
      <div v-if="hasFrequency" class="number-classification">
        <div class="classification-section hot-numbers">
          <h3>熱門號碼 (4次以上)</h3>
          <div class="number-list">
            <span 
              v-for="num in hotNumbers" 
              :key="num" 
              class="number-tag hot"
            >{{ String(num).padStart(2, '0') }}</span>
            <span v-if="hotNumbers.length === 0" class="no-data">無</span>
          </div>
        </div>
        
        <div class="classification-section normal-numbers">
          <h3>普通號碼 (2-3次)</h3>
          <div class="number-list">
            <span 
              v-for="num in normalNumbers" 
              :key="num" 
              class="number-tag normal"
            >{{ String(num).padStart(2, '0') }}</span>
            <span v-if="normalNumbers.length === 0" class="no-data">無</span>
          </div>
        </div>
        
        <div class="classification-section cold-numbers">
          <h3>冷門號碼 (0-1次)</h3>
          <div class="number-list">
            <span 
              v-for="num in coldNumbers" 
              :key="num" 
              class="number-tag cold"
            >{{ String(num).padStart(2, '0') }}</span>
            <span v-if="coldNumbers.length === 0" class="no-data">無</span>
          </div>
        </div>
      </div>
      <div v-else class="loading">載入中...</div>
    </div>

    <div class="card">
      <h2>📊 按出現次數排序</h2>
      
      <div v-if="hasFrequency" class="frequency-sorted-list">
        <div 
          v-for="item in numbersByFrequency" 
          :key="item.number"
          class="freq-sorted-item"
        >
          <span class="freq-number-sorted">{{ String(item.number).padStart(2, '0') }}</span>
          <span class="freq-count-sorted">{{ item.count }}次</span>
        </div>
      </div>
      <div v-else class="loading">載入中...</div>
    </div>

    <div class="card">
      <h2>📅 最近3期開獎號碼</h2>
      
      <div v-if="latestResults.length > 0" class="latest-results-list">
        <div 
          v-for="result in latestResults" 
          :key="result.id" 
          class="result-row"
        >
          <span class="result-period">{{ result.period }}期</span>
          <div class="result-numbers">
            <span 
              v-for="num in formatNumbers(result.numbers)" 
              :key="num" 
              class="number-tag ball"
            >{{ num }}</span>
          </div>
        </div>
      </div>
      <div v-else class="loading">載入中...</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watchEffect } from 'vue'
import { useLotteryStore } from '../stores/lottery'

const store = useLotteryStore()

// 最近3期開獎號碼
const latestResults = computed(() => {
  const results = store.results || []
  return results.slice(0, 3)
})

// 格式化號碼為陣列
const formatNumbers = (numbers) => {
  if (!numbers) return []
  return numbers.split(',').map(n => n.trim())
}

// 只取最近30期的資料
const recentResults = computed(() => {
  const results = store.results || []
  // 假設結果已經按日期排序，最新的在陣列前面
  return results.slice(0, 30)
})

// 計算每個號碼的出現頻率 (僅最近30期)
const frequency = computed(() => {
  const freq = {}
  for (let i = 1; i <= 39; i++) {
    freq[i] = 0
  }
  
  recentResults.value.forEach(row => {
    if (row.numbers) {
      const numbers = row.numbers.split(',').map(n => parseInt(n.trim()))
      numbers.forEach(num => {
        if (num >= 1 && num <= 39) {
          freq[num]++
        }
      })
    }
  })
  
  return freq
})

const hasFrequency = computed(() => {
  return recentResults.value.length > 0
})

const frequencyData = computed(() => {
  return frequency.value
})

// 取得柱狀圖高度
const getBarHeight = (count) => {
  const maxFreq = Math.max(...Object.values(frequency.value))
  if (maxFreq > 0) {
    return Math.round((count / maxFreq) * 60)
  }
  return 0
}

// 熱門號碼 (4次以上)
const hotNumbers = computed(() => {
  const nums = []
  for (let i = 1; i <= 39; i++) {
    if (frequency.value[i] >= 4) {
      nums.push(i)
    }
  }
  console.log('計算熱門號碼:', nums)
  return nums.sort((a, b) => a - b)
})

// 普通號碼 (2-3次)
const normalNumbers = computed(() => {
  const nums = []
  for (let i = 1; i <= 39; i++) {
    if (frequency.value[i] >= 2 && frequency.value[i] <= 3) {
      nums.push(i)
    }
  }
  console.log('計算普通號碼:', nums)
  return nums.sort((a, b) => a - b)
})

// 冷門號碼 (0-1次)
const coldNumbers = computed(() => {
  const nums = []
  for (let i = 1; i <= 39; i++) {
    if (frequency.value[i] <= 1) {
      nums.push(i)
    }
  }
  console.log('計算冷門號碼:', nums)
  return nums.sort((a, b) => a - b)
})

// 按出現次數排序的號碼列表
const numbersByFrequency = computed(() => {
  const nums = []
  for (let i = 1; i <= 39; i++) {
    if (frequency.value[i] > 0) {
      nums.push({ number: i, count: frequency.value[i] })
    }
  }
  return nums.sort((a, b) => b.count - a.count)
})

onMounted(() => {
  store.fetchResults()
})

// 在 console 列印熱門號碼
watchEffect(() => {
  if (hotNumbers.value.length > 0) {
    console.log('熱門號碼:', hotNumbers.value)
  }
})
</script>

<style scoped>
.latest-results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
}

.result-period {
  font-weight: bold;
  color: #000;
  min-width: 80px;
  font-size: 16px;
}

.result-numbers {
  display: flex;
  gap: 8px;
}

.frequency-chart {
  overflow-x: auto;
}

.frequency-grid {
  display: flex;
  gap: 4px;
  min-width: 600px;
}

.frequency-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 28px;
}

.freq-bar-container {
  height: 60px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.freq-bar {
  width: 13px;
  background-color: #4CAF50;
  min-height: 2px;
}

.freq-number {
  font-size: 10px;
  color: #FFD700;
  margin-top: 4px;
}

.freq-count {
  font-size: 10px;
  color: #FFD700;
  margin-bottom: 2px;
}

.number-classification {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.classification-section {
  padding: 12px;
  border-radius: 8px;
}

.classification-section h3 {
  margin: 0 0 8px 0;
  font-size: 14px;
}

.hot-numbers {
  background: #ffebee;
}

.hot-numbers h3 {
  color: #c62828;
}

.normal-numbers {
  background: #fff3e0;
}

.normal-numbers h3 {
  color: #e65100;
}

.cold-numbers {
  background: #e3f2fd;
}

.cold-numbers h3 {
  color: #1565c0;
}

.number-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.number-tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.number-tag.ball {
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
  padding: 0;
}

.number-tag.hot {
  background-color: #ef5350;
  color: white;
}

.number-tag.normal {
  background-color: #ff9800;
  color: white;
}

.number-tag.cold {
  background-color: #42a5f5;
  color: white;
}

.no-data {
  color: #999;
  font-style: italic;
}

.frequency-sorted-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.freq-sorted-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 13px;
}

.freq-number-sorted {
  font-weight: bold;
  color: #333;
}

.freq-count-sorted {
  color: #666;
  font-size: 12px;
}
</style>
