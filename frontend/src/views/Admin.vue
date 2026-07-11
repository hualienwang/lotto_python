<template>
  <div class="card">
    <h2>⚙️ 管理系統</h2>
    
    <form @submit.prevent="submitResult">
      <div class="form-group">
        <label for="period">期別：</label>
        <input 
          type="text" 
          id="period" 
          v-model="form.period" 
          placeholder="例如：113015"
          required
        >
      </div>
      
      <div class="form-group">
        <label for="drawDate">開獎日期：</label>
        <input 
          type="date" 
          id="drawDate" 
          v-model="form.draw_date" 
          required
        >
      </div>
      
      <div class="form-group">
        <label for="numbers">開獎號碼（5個號碼，用逗號分開）：</label>
        <input 
          type="text" 
          id="numbers" 
          v-model="form.numbers" 
          placeholder="例如：01, 05, 12, 23, 39"
          required
        >
      </div>
      
      <button type="submit" class="btn" :disabled="store.loading">
        {{ store.loading ? '儲存中...' : '儲存' }}
      </button>
    </form>
    
    <div class="sync-row">
      <button type="button" class="btn sync-btn" @click="syncRemoteResults" :disabled="store.loading">
        {{ store.loading ? '同步中...' : '下載官方開獎資料' }}
      </button>
      <span v-if="syncMessage" :class="syncClass">{{ syncMessage }}</span>
    </div>

    <div v-if="message" :class="messageClass" style="margin-top: 15px;">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useLotteryStore } from '../stores/lottery'

const store = useLotteryStore()
const message = ref('')
const messageClass = ref('')

const form = reactive({
  period: '',
  draw_date: '',
  numbers: ''
})

const syncMessage = ref('')
const syncClass = ref('')

const initPeriod = () => {
  store.fetchLatestResult().then(() => {
    if (store.latestResult?.period) {
      form.period = String(Number(store.latestResult.period) + 1)
    }
  })
}

onMounted(() => {
  initPeriod()
})

const submitResult = async () => {
  message.value = ''
  messageClass.value = ''
  
  try {
    // 格式化號碼
    const formattedNumbers = form.numbers
      .split(',')
      .map(n => n.trim())
      .map(n => n.padStart(2, '0'))
      .join(', ')
    
    const res = await store.addResult({
      period: form.period,
      draw_date: form.draw_date,
      numbers: formattedNumbers
    })
    
    if (res.success) {
      message.value = '開獎結果已成功儲存！'
      messageClass.value = 'success'
      // 清空表單
      form.period = ''
      form.draw_date = ''
      form.numbers = ''
    }
  } catch (err) {
    message.value = '儲存失敗：' + (err.response?.data?.message || err.message)
    messageClass.value = 'error'
  }
}

  const syncRemoteResults = async () => {
    syncMessage.value = ''
    syncClass.value = ''
    try {
      const res = await store.syncResults()
      if (res.success) {
        syncMessage.value = res.message || '官方開獎資料同步完成'
        syncClass.value = 'success'
        await store.fetchLatestResult()
        await store.fetchResults()
      }
    } catch (err) {
      syncMessage.value = '同步失敗：' + (err.response?.data?.message || err.message)
      syncClass.value = 'error'
    }
  }
</script>
