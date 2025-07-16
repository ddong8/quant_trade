// frontend/src/services/websocket.js
import { useDashboardStore } from '@/stores/dashboard';

let ws = null;

function connectWebSocket() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    console.log('WebSocket is already connected.');
    return;
  }
  
  const url = `ws://localhost:8000/api/v1/ws/`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    console.log(`Global WebSocket connected.`);
  };

  ws.onmessage = handleMessage;

  ws.onclose = () => {
    console.log('Global WebSocket disconnected. Attempting to reconnect in 5 seconds...');
    ws = null;
    setTimeout(connectWebSocket, 5000);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    ws.close();
  };
}

function handleMessage(event) {
  const dashboardStore = useDashboardStore();
  const message = JSON.parse(event.data);
  switch (message.type) {
    case 'log':
      dashboardStore.addLog(`[${new Date(message.data.timestamp).toLocaleTimeString()}] ${message.data.message}`);
      break;
    case 'live_update':
      dashboardStore.setLiveUpdate(message.data);
      break;
    case 'backtest_result': // 新增：统一处理回测结果
      // 将交易点位存入 orderEvents，方便图表绘制
      if(message.daily_pnl && message.daily_pnl.trades) {
         message.daily_pnl.trades.forEach(trade => {
            dashboardStore.addOrderEvent({
                date: trade.date,
                signal: trade.type,
                price: trade.price
            });
         });
         // 将数据格式修正为报告组件期望的格式
         message.daily_pnl = message.daily_pnl.pnl;
      }
      dashboardStore.setBacktestResult(message);
      break;
    default:
      // 其他消息类型可以忽略或打印
      // console.log("Received unknown message type:", message.type);
      break;
  }
}

function disconnectWebSocket() {
  if (ws) {
    ws.onclose = null;
    ws.close();
    ws = null;
  }
}

export { connectWebSocket, disconnectWebSocket };