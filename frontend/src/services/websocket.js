import { useDashboardStore } from '@/stores/dashboard'

let socket = null

const WS_URL = 'ws://localhost:8000/api/v1/ws/data';

export function connectWebSocket(onOpen, onClose, onError) {
  const dashboardStore = useDashboardStore()
  
  if (socket && socket.readyState === WebSocket.OPEN) {
    console.log("WebSocket is already connected.");
    return;
  }
  
  socket = new WebSocket(WS_URL)

  socket.onopen = () => {
    console.log('WebSocket Connected')
    if (onOpen) onOpen()
  }

  socket.onmessage = (event) => {
    const message = JSON.parse(event.data)
    if (message.type === 'pnl_update') {
      dashboardStore.addPnlData(message.data)
    } else if (message.type === 'log') {
      dashboardStore.addLog(message.data)
    } else if (message.type === 'backtest_result') {
      dashboardStore.setBacktestResult(message.data)
    } else if (message.type === 'account_update') {
      dashboardStore.setAccountEquity(message.data.equity)
    } else if (message.type === 'order_event') {
      dashboardStore.addOrderEvent(message.data)
    }
  }

  socket.onclose = () => {
    console.log('WebSocket Disconnected')
    if (onClose) onClose()
    socket = null
  }
  
  socket.onerror = (error) => {
    console.error('WebSocket Error:', error)
    if (onError) onError(error)
  }
}

export function disconnectWebSocket() {
  if (socket) {
    socket.close()
  }
}