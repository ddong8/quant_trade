import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useDashboardStore = defineStore('dashboard', () => {
  const pnlHistory = ref([])
  const logs = ref([])

  function addPnlData(data) {
    // 保持最多100个数据点
    if (pnlHistory.value.length > 100) {
      pnlHistory.value.shift()
    }
    pnlHistory.value.push(data)
  }

  function addLog(log) {
    // 保持最多100条日志
    if (logs.value.length > 100) {
      logs.value.shift()
    }
    const timestamp = new Date().toLocaleTimeString()
    logs.value.unshift(`[${timestamp}] [Strategy ${log.strategy_id}] ${log.message}`)
  }
  
  function clearData() {
    pnlHistory.value = []
    logs.value = []
  }

  return { pnlHistory, logs, addPnlData, addLog, clearData }
})