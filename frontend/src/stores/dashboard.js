import { defineStore } from 'pinia';

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    logs: [],
    orderEvents: [],
    backtestResult: null,
    backtestHistory: [],
    liveAccount: { equity: 0, available: 0 },
    livePosition: { symbol: '', volume: 0, average_price: 0 },
  }),
  actions: {
    addLog(log) {
      this.logs.unshift(log);
      if (this.logs.length > 200) {
        this.logs.pop();
      }
    },
    addOrderEvent(event) {
      this.orderEvents.push(event);
    },
    setBacktestResult(result) {
      this.backtestResult = result;
    },
    setLiveUpdate(data) {
      // 【修正】: 不替换整个对象，而是逐个属性更新
      if (data.account) {
        this.liveAccount.equity = data.account.equity;
        this.liveAccount.available = data.account.available;
      }
      if (data.position) {
        this.livePosition.symbol = data.position.symbol;
        this.livePosition.volume = data.position.volume;
        this.livePosition.average_price = data.position.average_price;
      }
    },
    clearData() {
      this.logs = [];
      this.orderEvents = [];
      this.backtestResult = null;
      // 清空时也逐个属性赋值，或者用新对象替换后再立即访问一次
      this.liveAccount = { equity: 0, available: 0 };
      this.livePosition = { symbol: '', volume: 0, average_price: 0 };
    },
  },
});