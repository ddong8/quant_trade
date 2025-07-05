import { useDashboardStore } from '@/stores/dashboard'

let socket = null

export function connectWebSocket(onOpen, onClose, onError) {
  const dashboardStore = useDashboardStore()
  
  if (socket && socket.readyState === WebSocket.OPEN) {
    console.log("WebSocket is already connected.");
    return;
  }
  
  socket = new WebSocket('ws://localhost:8000/ws/data')

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