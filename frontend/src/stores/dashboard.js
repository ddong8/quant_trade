import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiService from '../services/api'

export const useDashboardStore = defineStore('dashboard', () => {
  const pnlHistory = ref([])
  const logs = ref([])
  const backtestResult = ref(null)
  const accountEquity = ref(null)
  const orderEvents = ref([])
  const backtestHistory = ref([])

  async function fetchBacktestHistory(strategyId) {
    try {
      const response = await apiService.getBacktestHistoryForStrategy(strategyId)
      backtestHistory.value = response.data
    } catch (error) {
      console.error('Error fetching backtest history:', error)
      // Handle error appropriately in the UI
    }
  }

  async function runBacktest(strategyId, params) {
    try {
      const response = await apiService.runBacktest(strategyId, params)
      // After starting a new backtest, refresh the history
      await fetchBacktestHistory(strategyId)
      return response.data // Return the response which might contain the task ID
    } catch (error) {
      console.error('Error running backtest:', error)
      // Handle error appropriately in the UI
      throw error
    }
  }

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

  function setAccountEquity(equity) {
    accountEquity.value = equity
  }

  function addOrderEvent(event) {
    orderEvents.value.push(event)
  }
  
  function clearData() {
    pnlHistory.value = []
    logs.value = []
    backtestResult.value = null
    accountEquity.value = null
    orderEvents.value = []
    backtestHistory.value = []
  }

  return { 
    pnlHistory, 
    logs, 
    backtestResult, 
    accountEquity, 
    orderEvents, 
    backtestHistory,
    fetchBacktestHistory,
    runBacktest,
    addPnlData, 
    addLog, 
    setBacktestResult, 
    setAccountEquity, 
    addOrderEvent, 
    clearData 
  }
})
