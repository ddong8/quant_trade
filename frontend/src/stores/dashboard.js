import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useDashboardStore = defineStore('dashboard', () => {
  const pnlHistory = ref([])
  const logs = ref([])
  const backtestResult = ref(null)

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

  function setBacktestResult(result) {
    backtestResult.value = result
  }
  
  function clearData() {
    pnlHistory.value = []
    logs.value = []
    backtestResult.value = null
  }

  return { pnlHistory, logs, backtestResult, addPnlData, addLog, setBacktestResult, clearData }
})