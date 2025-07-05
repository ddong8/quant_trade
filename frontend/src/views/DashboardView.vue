<template>
  <n-space vertical :size="24">
    <n-alert :title="wsStatusTitle" :type="wsStatusType" closable>
      {{ wsStatusMessage }}
    </n-alert>

    <n-grid :cols="4" :x-gap="24">
        <n-gi>
            <n-statistic label="账户总权益" tabular-nums>
                <template #prefix>¥</template>
                {{ (100000 + latestPnl).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            </n-statistic>
        </n-gi>
        <n-gi>
            <n-statistic label="今日盈亏">
                 <template #prefix>¥</template>
                 <n-number-animation :from="0" :to="latestPnl" :precision="2" />
            </n-statistic>
        </n-gi>
    </n-grid>

    <n-card title="实时盈亏曲线" :bordered="false">
      <div ref="pnlChartRef" style="height: 400px;"></div>
    </n-card>

    <n-card title="策略实时日志" :bordered="false">
      <n-log :log="logText" :rows="15" />
    </n-card>

  </n-space>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useMessage, NSpace, NGrid, NGi, NCard, NStatistic, NNumberAnimation, NLog, NAlert } from 'naive-ui';
import * as echarts from 'echarts';
import { useDashboardStore } from '@/stores/dashboard';
import { connectWebSocket, disconnectWebSocket } from '@/services/websocket';

const message = useMessage();
const dashboardStore = useDashboardStore();

// WebSocket 状态
const wsStatus = ref('disconnected'); // 'connecting', 'connected', 'disconnected', 'error'
const wsStatusTitle = computed(() => {
  const titles = {
    connected: "实时通道已连接",
    disconnected: "实时通道已断开",
    error: "实时通道连接错误",
  };
  return titles[wsStatus.value];
});
const wsStatusType = computed(() => ({ connected: "success", disconnected: "warning", error: "error" }[wsStatus.value]));
const wsStatusMessage = computed(() => {
    const messages = {
    connected: "正在接收来自服务器的实时数据。",
    disconnected: "已与服务器断开连接，将尝试重新连接。",
    error: "连接发生错误，请检查后端服务是否正常运行。",
  };
  return messages[wsStatus.value];
})

// PnL Chart
const pnlChartRef = ref(null);
let pnlChart = null;

const latestPnl = computed(() => {
    const history = dashboardStore.pnlHistory;
    return history.length > 0 ? history[history.length - 1].pnl : 0;
});

const logText = computed(() => dashboardStore.logs.join('\n'));

const initChart = () => {
  pnlChart = echarts.init(pnlChartRef.value, 'dark');
  pnlChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'time',
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitLine: { lineStyle: { type: 'dashed', color: '#333' } }
    },
    series: [{
      data: [],
      type: 'line',
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#00c853' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
          offset: 0,
          color: 'rgba(0, 200, 83, 0.3)'
        }, {
          offset: 1,
          color: 'rgba(0, 200, 83, 0)'
        }])
      }
    }],
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true }
  });
};

watch(() => dashboardStore.pnlHistory, (newHistory) => {
  if (pnlChart) {
    const chartData = newHistory.map(item => [item.timestamp * 1000, item.pnl]);
    pnlChart.setOption({
      series: [{ data: chartData }]
    });
  }
}, { deep: true });

onMounted(() => {
  dashboardStore.clearData();
  initChart();
  connectWebSocket(
    () => { wsStatus.value = 'connected'; message.success("实时通道已连接") },
    () => { wsStatus.value = 'disconnected'; message.warning("实时通道已断开") },
    () => { wsStatus.value = 'error'; message.error("实时通道连接失败") }
  );
  window.addEventListener('resize', () => pnlChart?.resize());
});

onUnmounted(() => {
  disconnectWebSocket();
  pnlChart?.dispose();
  window.removeEventListener('resize', () => pnlChart?.resize());
});
</script>