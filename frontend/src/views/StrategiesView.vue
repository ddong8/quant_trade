<template>
  <n-space vertical :size="24">
    <!-- 顶部状态 & 统计 -->
    <n-alert :title="wsStatusTitle" :type="wsStatusType" closable>
      {{ wsStatusMessage }}
    </n-alert>

    <n-grid :cols="4" :x-gap="24">
      <n-gi>
        <n-statistic label="账户总权益" tabular-nums>
          <template #prefix>¥</template>
          <n-number-animation :from="0" :to="accountEquity || 0" :precision="2" />
        </n-statistic>
      </n-gi>
      <n-gi>
        <n-statistic label="今日盈亏">
          <template #prefix>¥</template>
          <n-number-animation :from="0" :to="latestPnl" :precision="2" />
        </n-statistic>
      </n-gi>
    </n-grid>

    <!-- 实时图表和日志 -->
    <n-card title="实时盈亏曲线" :bordered="false">
      <div ref="pnlChartRef" style="height: 400px;"></div>
    </n-card>

    <!-- 策略管理 -->
    <n-card title="策略管理">
      <template #header-extra>
        <n-button type="primary" @click="showCreateModal = true">创建新策略</n-button>
      </template>
      <div v-if="strategies.length === 0">
        <n-empty description="暂无策略，请创建一个新策略"></n-empty>
      </div>
      <n-grid v-else :x-gap="24" :y-gap="24" :cols="3">
        <n-gi v-for="strategy in strategies" :key="strategy.id">
          <n-card :title="strategy.name">
            <template #header-extra>
              <n-tag :type="statusMap[strategy.status]?.type || 'default'">
                {{ backtesting_ids.has(strategy.id) ? '回测中' : (statusMap[strategy.status]?.text || '未知') }}
              </n-tag>
            </template>
            <p>{{ strategy.description }}</p>
            <template #action>
              <n-space justify="end">
                <n-button size="small" @click="runStrategy(strategy.id)" :disabled="strategy.status === 'running' || backtesting_ids.has(strategy.id)">运行</n-button>
                <n-button size="small" @click="stopStrategy(strategy.id)" :disabled="strategy.status !== 'running' && !backtesting_ids.has(strategy.id)">停止</n-button>
                <n-button size="small" type="primary" ghost @click="openEditModal(strategy)">编辑</n-button>
                <n-button size="small" type="info" ghost @click="openBacktestModal(strategy)" :disabled="backtesting_ids.has(strategy.id)">回测</n-button>
                <n-button size="small" type="default" ghost @click="openHistoryModal(strategy)">历史报告</n-button>
                <n-button size="small" type="error" ghost @click="deleteStrategy(strategy.id)">删除</n-button>
              </n-space>
            </template>
          </n-card>
        </n-gi>
      </n-grid>
    </n-card>

    <n-card title="策略实时日志">
      <n-log :log="logText" :rows="15" />
    </n-card>

    <!-- All Modals -->
    <n-modal v-model:show="showCreateModal" preset="card" style="width: 600px;" title="创建新策略">
      <n-form @submit.prevent="handleCreateStrategy">
        <n-form-item label="策略名称"><n-input v-model:value="newStrategyData.name" /></n-form-item>
        <n-form-item label="策略描述"><n-input v-model:value="newStrategyData.description" type="textarea" /></n-form-item>
        <n-button type="primary" attr-type="submit" block>创建</n-button>
      </n-form>
    </n-modal>

    <n-modal v-model:show="showEditModal" preset="card" style="width: 80vw; max-width: 1000px;" title="编辑策略">
      <n-form-item label="策略代码">
        <div ref="editorContainer" style="width: 100%; height: 500px; border: 1px solid #ccc;"></div>
      </n-form-item>
      <template #footer><n-button type="primary" @click="handleUpdateStrategy">保存代码</n-button></template>
    </n-modal>

    <n-modal v-model:show="showBacktestModal" preset="card" style="width: 600px;" title="运行回测">
      <n-form @submit.prevent="handleRunBacktest">
        <n-form-item path="symbol" label="合约代码">
            <n-input v-model:value="backtestParams.symbol" @keydown.enter.prevent />
          </n-form-item>
          <n-form-item path="duration" label="K线周期">
            <n-select v-model:value="backtestParams.duration" :options="durationOptions" />
          </n-form-item>
        <n-form-item label="开始日期"><n-date-picker v-model:value="backtestParams.start_date" type="date" style="width: 100%;" /></n-form-item>
        <n-form-item label="结束日期"><n-date-picker v-model:value="backtestParams.end_date" type="date" style="width: 100%;" /></n-form-item>
        <n-button type="primary" attr-type="submit" block>开始回测</n-button>
      </n-form>
    </n-modal>

    <n-modal v-model:show="showBacktestReport" preset="card" style="width: 90vw; max-width: 900px;" title="回测报告">
      <n-spin :show="!backtestResult">
        <div v-if="backtestResult">
          <n-h3>权益曲线</n-h3>
          <div ref="backtestChartContainer" style="width: 100%; height: 400px;"></div>
          <n-h3>绩效指标</n-h3>
          <n-descriptions label-placement="left" bordered :column="2">
            <n-descriptions-item v-for="(value, key) in backtestResult.summary" :key="key" :label="key">
              {{ formatSummaryValue(key, value) }}
            </n-descriptions-item>
          </n-descriptions>
        </div>
        <template #footer><n-button @click="closeReportModal">关闭</n-button></template>
      </n-spin>
    </n-modal>

    <n-modal v-model:show="showHistoryModal" preset="card" style="width: 800px;" title="历史回测报告">
      <n-data-table
        :columns="historyColumns"
        :data="backtestHistory"
        :pagination="false"
        :bordered="false"
      />
    </n-modal>

  </n-space>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive, nextTick, watch, computed } from 'vue';
import { NSpace, NGrid, NGi, NCard, NTag, NButton, useMessage, NSpin, NForm, NFormItem, NInput, NEmpty, NModal, useDialog, NLog, NDatePicker, NDescriptions, NDescriptionsItem, NAlert, NStatistic, NNumberAnimation, NSelect, NDataTable } from 'naive-ui';
import * as monaco from 'monaco-editor';
import * as echarts from 'echarts';
import api from '@/services/api';
import { useDashboardStore } from '@/stores/dashboard';
import { connectWebSocket, disconnectWebSocket } from '@/services/websocket';
import { storeToRefs } from 'pinia';
import { h } from 'vue';

// --- Store and Services ---
const message = useMessage();
const dialog = useDialog();
const dashboardStore = useDashboardStore();
const { pnlHistory, logs, accountEquity, orderEvents, backtestResult, backtestHistory } = storeToRefs(dashboardStore);

// --- Local State ---
const strategies = ref([]);
const backtesting_ids = ref(new Set());
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showBacktestModal = ref(false);
const showBacktestReport = ref(false);
const showHistoryModal = ref(false);
const activeStrategy = ref(null);
const newStrategyData = reactive({ name: '', description: '' });
const editStrategyData = reactive({ id: null, code: '' });
const backtestParams = reactive({
  strategy_id: null,
  symbol: 'SHFE.rb2501',
  duration: '1d',
  start_date: null,
  end_date: null
});

const durationOptions = [
  { label: '日线', value: '1d' },
  { label: '1小时', value: '1h' },
  { label: '15分钟', value: '15m' },
  { label: '5分钟', value: '5m' },
  { label: '1分钟', value: '1m' },
];
const wsStatus = ref('disconnected');
let pollingInterval = null;

// --- Monaco Editor ---
const editorContainer = ref(null);
let monacoInstance = null;

// --- ECharts Instances ---
const pnlChartRef = ref(null);
let pnlChart = null;
const backtestChartContainer = ref(null);
let backtestChart = null;

// --- Computed Properties ---
const logText = computed(() => logs.value.join('\n'));
// const pnlHistory = computed(() => dashboardStore.pnlHistory); // 保持对store的计算属性引用
const latestPnl = computed(() => pnlHistory.value.length > 0 ? pnlHistory.value[pnlHistory.value.length - 1].pnl : 0);
const wsStatusTitle = computed(() => ({
  connected: "实时通道已连接",
  disconnected: "实时通道已断开",
  error: "实时通道连接错误",
}[wsStatus.value]));
const wsStatusType = computed(() => ({ connected: "success", disconnected: "warning", error: "error" }[wsStatus.value]));
const wsStatusMessage = computed(() => ({
  connected: "正在接收来自服务器的实时数据。",
  disconnected: "已与服务器断开连接。",
  error: "连接发生错误，请检查后端服务是否正常运行。",
}[wsStatus.value]));
const statusMap = {
  stopped: { text: '已停止', type: 'default' },
  running: { text: '运行中', type: 'success' },
  error: { text: '错误', type: 'error' },
};

const historyColumns = [
    { title: '回测ID', key: 'id' },
    { title: '创建时间', key: 'created_at', render: (row) => new Date(row.created_at).toLocaleString() },
    { title: '状态', key: 'status' },
    { title: '夏普比率', key: 'sharpe_ratio', render: (row) => row.sharpe_ratio ? row.sharpe_ratio.toFixed(2) : 'N/A' },
    { title: '最大回撤', key: 'max_drawdown', render: (row) => row.max_drawdown ? `${(row.max_drawdown * 100).toFixed(2)}%` : 'N/A' },
    {
        title: '操作',
        key: 'actions',
        render(row) {
            return h(
                NButton,
                {
                    size: 'small',
                    onClick: () => showReportFromHistory(row.id),
                    disabled: row.status !== 'SUCCESS'
                },
                { default: () => '查看报告' }
            );
        }
    }
];

// --- Charting Functions ---
const initPnlChart = () => {
  pnlChart = echarts.init(pnlChartRef.value, 'dark');
  pnlChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'time', splitLine: { show: false } },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { type: 'dashed', color: '#333' } } },
    series: [{
      name: 'PnL',
      data: [],
      type: 'line',
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#00c853' },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(0, 200, 83, 0.3)' }, { offset: 1, color: 'rgba(0, 200, 83, 0)' }]) }
    }],
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true }
  });
};

const renderBacktestChart = (result) => {
  if (!backtestChartContainer.value) return;
  backtestChart = echarts.init(backtestChartContainer.value);
  backtestChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: result.daily_pnl.map(d => d.date) },
    yAxis: { type: 'value', name: '权益' },
    series: [{ name: '每日权益', type: 'line', data: result.daily_pnl.map(d => d.pnl), smooth: true, showSymbol: false }]
  });
};

// --- CRUD Functions ---
async function fetchStrategies() {
  try {
    const { data } = await api.getStrategies();
    strategies.value = data;
  } catch (error) {
    message.error('加载策略列表失败');
  }
}

async function handleCreateStrategy() {
  try {
    const { data: newStrategy } = await api.createStrategy(newStrategyData);
    message.success('策略创建成功');
    showCreateModal.value = false;
    newStrategyData.name = '';
    newStrategyData.description = '';
    await fetchStrategies();
    const strategyToEdit = strategies.value.find(s => s.id === newStrategy.id);
    if (strategyToEdit) {
      openEditModal(strategyToEdit);
    }
  } catch (error) {
    message.error('策略创建失败');
  }
}

function openEditModal(strategy) {
  activeStrategy.value = strategy;
  editStrategyData.id = strategy.id;
  editStrategyData.code = '// Loading...';
  showEditModal.value = true;

  api.getStrategyScript(strategy.id).then(response => {
    editStrategyData.code = response.data.script_content || `// Code for ${strategy.name}`;
    nextTick(() => {
      if (editorContainer.value) {
        if (!monacoInstance) {
          monacoInstance = monaco.editor.create(editorContainer.value, {
            value: editStrategyData.code,
            language: 'python',
            theme: 'vs-dark'
          });
        } else {
          monacoInstance.setValue(editStrategyData.code);
        }
      }
    });
  }).catch(() => message.error('Failed to load strategy code.'));
}

async function handleUpdateStrategy() {
  if (!monacoInstance) return;
  const newCode = monacoInstance.getValue();
  try {
    await api.updateStrategy(editStrategyData.id, { script_content: newCode });
    message.success('代码保存成功');
    showEditModal.value = false;
  } catch (error) {
    message.error('代码保存失败');
  }
}

async function runStrategy(id) {
  try {
    await api.startStrategy(id);
    message.success('策略已启动');
    fetchStrategies();
  }
  catch (error) {
    message.error('启动策略失败');
  }
}

async function stopStrategy(id) {
  try {
    await api.stopStrategy(id);
    message.success('策略已停止');
    backtesting_ids.value.delete(id);
    disconnectWebSocket();
    fetchStrategies();
  } catch (error) {
    message.error('停止策略失败');
  }
}

function deleteStrategy(id) {
  dialog.warning({
    title: '确认删除',
    content: '确定要删除这个策略吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deleteStrategy(id);
        message.success('策略已删除');
        fetchStrategies();
      } catch (error) {
        message.error('删除策略失败');
      }
    },
  });
}

// --- Backtest Functions ---
function openBacktestModal(strategy) {
  backtestParams.strategy_id = strategy.id;
  backtestParams.start_date = new Date().setFullYear(new Date().getFullYear() - 1);
  backtestParams.end_date = Date.now();
  showBacktestModal.value = true;
}

import { sendWebSocketMessage } from '@/services/websocket';

// ... (rest of the script setup)

async function handleRunBacktest() {
  try {
    dashboardStore.clearData(); // 清空上次回测的日志和数据
    const params = {
      symbol: backtestParams.symbol,
      duration: backtestParams.duration,
      start_dt: new Date(backtestParams.start_date).toISOString(),
      end_dt: new Date(backtestParams.end_date).toISOString(),
    };

    // 1. 直接调用API，后端将创建记录并启动Celery任务
    const { data } = await api.runBacktest(backtestParams.strategy_id, params);
    const backtestId = response.backtest_id;

    message.info(`回测任务已启动 (ID: ${backtestId})，等待实时数据...`);
    backtesting_ids.value.add(backtestParams.strategy_id);
    showBacktestModal.value = false;

    // 2. 连接WebSocket以接收实时进度
    connectWebSocket(
      backtestId,
      () => { wsStatus.value = 'connected'; }, // onOpen
      () => { // onClose
          wsStatus.value = 'disconnected';
          backtesting_ids.value.delete(backtestParams.strategy_id);
          fetchStrategies(); // 刷新策略状态
      },
      () => { wsStatus.value = 'error'; } // onError
    );

  } catch (error) {
    const errorMsg = error.response?.data?.detail || '启动回测失败';
    message.error(errorMsg);
    backtesting_ids.value.delete(backtestParams.strategy_id);
  }
}

async function openHistoryModal(strategy) {
    activeStrategy.value = strategy;
    showHistoryModal.value = true;
    await fetchHistoryAndStartPolling(strategy.id);
}

async function fetchHistoryAndStartPolling(strategyId) {
    try {
        const { data } = await api.getBacktestHistory(strategyId);
        backtestHistory.value = data;

        const isAnyRunning = data.some(b => ['PENDING', 'RUNNING'].includes(b.status));
        
        if (isAnyRunning && !pollingInterval) {
            // 如果有正在运行的任务且没有轮询器，则启动
            startPolling(strategyId);
        } else if (!isAnyRunning && pollingInterval) {
            // 如果没有正在运行的任务但轮询器还在，则停止
            stopPolling();
        }

    } catch (error) {
        message.error('加载历史报告失败');
        stopPolling();
    }
}

async function showReportFromHistory(backtestId) {
    try {
        const { data } = await api.getBacktestReport(backtestId);
        dashboardStore.setBacktestResult(data);
        showHistoryModal.value = false; // 关闭历史记录弹窗
        showBacktestReport.value = true; // 显示报告弹窗
        nextTick(() => renderBacktestChart(data));
    } catch (error) {
        message.error('加载报告详情失败');
    }
}

function startPolling(strategyId) {
  stopPolling(); // 先确保旧的已停止
  pollingInterval = setInterval(() => {
    fetchHistoryAndStartPolling(strategyId);
  }, 5000);
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}

const formatSummaryValue = (key, value) => {
  const keyName = key.toLowerCase();
  if (typeof value !== 'number') return value;

  if (keyName.includes('ratio') || keyName.includes('rate') || keyName.includes('return') || keyName.includes('drawdown')) {
    return `${(value * 100).toFixed(2)}%`;
  }
  return value.toFixed(2);
};

const closeReportModal = () => {
  showBacktestReport.value = false;
  dashboardStore.setBacktestResult(null);
  disconnectWebSocket();
  if (backtestChart) {
    backtestChart.dispose();
    backtestChart = null;
  }
};

// --- Watchers ---
watch(pnlHistory, (newHistory) => {
  if (pnlChart) {
    // Backend sends `date` string, not `timestamp`. ECharts time axis handles Date objects.
    const chartData = newHistory.map(item => [new Date(item.date), item.pnl]);
    pnlChart.setOption({
      series: [{
        data: chartData
      }]
    });
  }
}, { deep: true });

watch(orderEvents, (newEvent) => {
  if (pnlChart && newEvent && newEvent.length > 0) {
    const lastEvent = newEvent[newEvent.length - 1];
    const markPoint = {
      symbol: lastEvent.direction === 'BUY' ? 'arrow' : 'pin',
      symbolSize: 15,
      data: [{
        name: 'Order',
        coord: [lastEvent.timestamp, lastEvent.price],
        value: `${lastEvent.direction} @ ${lastEvent.price}`,
        itemStyle: { color: lastEvent.direction === 'BUY' ? '#ff4d4f' : '#52c41a' }
      }]
    };
    const currentOptions = pnlChart.getOption();
    const existingMarkPoints = currentOptions.series[0].markPoint?.data || [];
    pnlChart.setOption({ series: [{ markPoint: { data: [...existingMarkPoints, ...markPoint.data] } }] });
  }
}, { deep: true });

watch(backtestResult, (newResult) => {
  if (newResult) {
    backtesting_ids.value.delete(newResult.strategy_id);
    fetchStrategies(); // Refresh strategies to get updated backtest_results list

    // 将回测结果添加到日志中
    const timestamp = new Date().toLocaleTimeString();
    const summaryText = Object.entries(newResult.summary)
      .map(([key, value]) => `${key}: ${formatSummaryValue(key, value)}`)
      .join(', ');
    const logMessage = `[${timestamp}] [Backtest Result for Strategy ${newResult.strategy_id}] ${summaryText}`;
    logs.value.unshift(logMessage);

    showBacktestReport.value = true;
    nextTick(() => renderBacktestChart(newResult));
  }
});

watch(showEditModal, (newValue) => {
  if (!newValue && monacoInstance) {
    monacoInstance.dispose();
    monacoInstance = null;
  }
});

watch(showHistoryModal, (newValue) => {
  if (!newValue) {
    stopPolling();
  }
});

// --- Lifecycle Hooks ---
onMounted(() => {
  dashboardStore.clearData();
  fetchStrategies();
  initPnlChart();
  window.addEventListener('resize', () => pnlChart?.resize());
});

onUnmounted(() => {
  disconnectWebSocket();
  stopPolling();
  pnlChart?.dispose();
  backtestChart?.dispose();
  if (monacoInstance) monacoInstance.dispose();
  window.removeEventListener('resize', () => pnlChart?.resize());
});
</script>