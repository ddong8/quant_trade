<template>
  <n-space vertical :size="24">
    <!-- 顶部状态 & 统计 -->
    
    <n-grid :cols="4" :x-gap="24">
      <n-gi>
        <n-statistic label="账户总权益" tabular-nums>
          <template #prefix>¥</template>
          {{ liveAccount.equity ? liveAccount.equity.toFixed(2) : '0.00' }}
        </n-statistic>
      </n-gi>
      <n-gi>
        <n-statistic label="可用资金">
          <template #prefix>¥</template>
          {{ liveAccount.available ? liveAccount.available.toFixed(2) : '0.00' }}
        </n-statistic>
      </n-gi>
      <n-gi>
        <n-statistic :label="`持仓合约 (${livePosition.symbol || '无'})`">
          {{ livePosition.volume || 0 }}
        </n-statistic>
      </n-gi>
       <n-gi>
        <n-statistic label="持仓均价">
          <template #prefix>¥</template>
          {{ livePosition.average_price ? livePosition.average_price.toFixed(2) : '0.00' }}
        </n-statistic>
      </n-gi>
    </n-grid>

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
        <n-form-item label="选择模板">
          <n-select v-model:value="newStrategyData.template_name" :options="strategyTemplateOptions" />
        </n-form-item>
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
        
        <n-h4>交易设置</n-h4>
        <n-form-item label="手续费率 (%)">
          <n-input-number v-model:value="backtestParams.commission_rate" :min="0" :step="0.0001">
            <template #suffix>%</template>
          </n-input-number>
        </n-form-item>
        <n-form-item label="滑点 (元)">
          <n-input-number v-model:value="backtestParams.slippage" :min="0" :step="0.01" />
        </n-form-item>

        <n-h4>参数优化</n-h4>
        <n-p depth="3">如果要进行参数优化，请在此处添加参数。否则将使用策略文件中的默认值进行单次回测。</n-p>
        
        <div v-for="(param, index) in optimParams" :key="index" style="display: flex; gap: 8px; margin-bottom: 8px; align-items: center;">
          <n-input v-model:value="param.name" placeholder="参数名" />
          <n-input-number v-model:value="param.start" placeholder="开始值" style="min-width: 80px;" />
          <n-input-number v-model:value="param.end" placeholder="结束值" style="min-width: 80px;" />
          <n-input-number v-model:value="param.step" placeholder="步长" style="min-width: 80px;" />
          <n-button @click="removeOptimParam(index)" text type="error">删除</n-button>
        </div>
        <n-button @click="addOptimParam" dashed block>添加优化参数</n-button>

        <n-button type="primary" attr-type="submit" block style="margin-top: 24px;">开始</n-button>
      </n-form>
    </n-modal>

    <n-modal v-model:show="showBacktestReport" preset="card" style="width: 90vw; max-width: 900px;" title="回测报告">
      <n-spin :show="!backtestResult">
        <div v-if="backtestResult">
          <n-h3>权益曲线</n-h3>
          <div ref="backtestChartContainer" style="width: 100%; height: 400px;"></div>
          <n-h3>绩效指标</n-h3>
          <n-descriptions label-placement="left" bordered :column="4">
            <n-descriptions-item label="初始资金">{{ formatSummaryValue('initial_equity', backtestResult.summary.initial_equity) }}</n-descriptions-item>
            <n-descriptions-item label="最终资金">{{ formatSummaryValue('final_equity', backtestResult.summary.final_equity) }}</n-descriptions-item>
            <n-descriptions-item label="总收益率">{{ formatSummaryValue('total_return', backtestResult.summary.total_return) }}</n-descriptions-item>
            <n-descriptions-item label="年化收益率">{{ formatSummaryValue('annualized_return', backtestResult.summary.annualized_return) }}</n-descriptions-item>
            
            <n-descriptions-item label="年化波动率">{{ formatSummaryValue('annualized_volatility', backtestResult.summary.annualized_volatility) }}</n-descriptions-item>
            <n-descriptions-item label="最大回撤">{{ formatSummaryValue('max_drawdown', backtestResult.summary.max_drawdown) }}</n-descriptions-item>
            <n-descriptions-item label="夏普比率">{{ formatSummaryValue('sharpe_ratio', backtestResult.summary.sharpe_ratio) }}</n-descriptions-item>
            <n-descriptions-item label="索提诺比率">{{ formatSummaryValue('sortino_ratio', backtestResult.summary.sortino_ratio) }}</n-descriptions-item>

            <n-descriptions-item label="卡玛比率">{{ formatSummaryValue('calmar_ratio', backtestResult.summary.calmar_ratio) }}</n-descriptions-item>
            <n-descriptions-item label="总交易次数">{{ formatSummaryValue('total_trades', backtestResult.summary.total_trades) }}</n-descriptions-item>
            <n-descriptions-item label="胜率">{{ formatSummaryValue('win_rate', backtestResult.summary.win_rate) }}</n-descriptions-item>
            <n-descriptions-item label="盈亏比">{{ formatSummaryValue('profit_factor', backtestResult.summary.profit_factor) }}</n-descriptions-item>
          </n-descriptions>
          
          <div v-if="backtestResult.summary.params">
            <n-h4>优化参数</n-h4>
            <n-descriptions label-placement="left" bordered :column="1">
              <n-descriptions-item label="参数组合">
                {{ formatSummaryValue('params', backtestResult.summary.params) }}
              </n-descriptions-item>
            </n-descriptions>
          </div>

          <n-h3>交易明细</n-h3>
          <n-data-table
            :columns="tradeHistoryColumns"
            :data="backtestResult.daily_pnl.trades"
            :pagination="{ pageSize: 10 }"
            :bordered="false"
            size="small"
          />
        </div>
        <template #footer><n-button @click="closeReportModal">关闭</n-button></template>
      </n-spin>
    </n-modal>

    <n-modal v-model:show="showHistoryModal" preset="card" style="width: 800px;" title="历史回测报告">
      <n-data-table
        :columns="historyColumns"
        :data="groupedHistory"
        :pagination="false"
        :bordered="false"
      />
    </n-modal>

    <n-modal v-model:show="showOptimizationReportModal" preset="card" style="width: 90vw; max-width: 1000px;" title="参数优化报告">
      <n-spin :show="!optimizationResults.length">
        <div ref="optimizationChartContainer" style="width: 100%; height: 500px;"></div>
        <template #footer><n-button @click="showOptimizationReportModal = false">关闭</n-button></template>
      </n-spin>
    </n-modal>

  </n-space>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive, nextTick, watch, computed } from 'vue';
import { NSpace, NGrid, NGi, NCard, NTag, NButton, useMessage, NSpin, NForm, NFormItem, NInput, NEmpty, NModal, useDialog, NLog, NDatePicker, NDescriptions, NDescriptionsItem, NAlert, NStatistic, NNumberAnimation, NSelect, NDataTable, NInputNumber, NH4, NP } from 'naive-ui';
import * as monaco from 'monaco-editor';
import * as echarts from 'echarts';
import api from '@/services/api';
import { useDashboardStore } from '@/stores/dashboard';
import { connectWebSocket, disconnectWebSocket } from '@/services/websocket';
import { storeToRefs } from 'pinia';
import { h } from 'vue';

const message = useMessage();
const dialog = useDialog();
const dashboardStore = useDashboardStore();
const { logs, orderEvents, backtestResult, backtestHistory, liveAccount, livePosition } = storeToRefs(dashboardStore);

const strategies = ref([]);
const backtesting_ids = ref(new Set());
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showBacktestModal = ref(false);
const showBacktestReport = ref(false);
const showHistoryModal = ref(false);
const showOptimizationReportModal = ref(false);
const activeStrategy = ref(null);
const newStrategyData = reactive({ name: '', description: '', template_name: 'empty' });
const editStrategyData = reactive({ id: null, content: '' });
const backtestParams = reactive({
  strategy_id: null,
  symbol: 'SHFE.rb2501',
  duration: '1d',
  start_date: null,
  end_date: null,
  commission_rate: 0.0003, // 0.03%
  slippage: 0.01, // 1 tick or price unit
});
const optimParams = ref([]);
const optimizationResults = ref([]);

const strategyTemplateOptions = [
  { label: '均线交叉策略模板', value: 'ma_crossover' },
  { label: '空策略', value: 'empty' },
];

const addOptimParam = () => {
  optimParams.value.push({ name: '', start: 0, end: 0, step: 1 });
};
const removeOptimParam = (index) => {
  optimParams.value.splice(index, 1);
};

const durationOptions = [
  { label: '日线', value: '1d' },
  { label: '1小时', value: '1h' },
  { label: '15分钟', value: '15m' },
  { label: '5分钟', value: '5m' },
  { label: '1分钟', value: '1m' },
];
const wsStatus = ref('disconnected');
let pollingInterval = null;

const editorContainer = ref(null);
let monacoInstance = null;

const backtestChartContainer = ref(null);
let backtestChart = null;
const optimizationChartContainer = ref(null);
let optimizationChart = null;

const logText = computed(() => logs.value.join('\n'));
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
  running: { text: '模拟运行中', type: 'success' },
  error: { text: '错误', type: 'error' },
};

const groupedHistory = computed(() => {
  if (!backtestHistory.value || backtestHistory.value.length === 0) return [];

  const optimizations = {};
  const singleRuns = [];

  backtestHistory.value.forEach(run => {
    if (run.optimization_id) {
      if (!optimizations[run.optimization_id]) {
        optimizations[run.optimization_id] = {
          isGroup: true,
          optimization_id: run.optimization_id,
          created_at: run.created_at, // Use the first run's creation time
          status: 'COMPLETED', // Assume completed if we have results
          run_count: 0,
          best_sharpe: -Infinity,
          children: [],
        };
      }
      const group = optimizations[run.optimization_id];
      group.run_count++;
      group.children.push(run);
      if (run.status === 'PENDING' || run.status === 'RUNNING') {
        group.status = 'RUNNING';
      }
      const sharpe = run.summary?.sharpe_ratio;
      if (sharpe && sharpe > group.best_sharpe) {
        group.best_sharpe = sharpe;
      }

    } else {
      singleRuns.push(run);
    }
  });

  const sortedOptimizations = Object.values(optimizations).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  return [...sortedOptimizations, ...singleRuns];
});

const historyColumns = [
    { title: '类型', key: 'type', render: (row) => row.isGroup ? h(NTag, {type: 'info'}, {default: () => '优化'}) : h(NTag, {}, {default: () => '单次'}) },
    { title: '创建时间', key: 'created_at', render: (row) => new Date(row.created_at).toLocaleString() },
    { title: '状态', key: 'status' },
    { 
      title: '详情', 
      key: 'details',
      render(row) {
        if (row.isGroup) {
          return `共 ${row.run_count} 次运行, 最高夏普: ${row.best_sharpe.toFixed(2)}`;
        } else {
          const params = row.summary?.params;
          return params ? JSON.stringify(params) : '默认参数';
        }
      }
    },
    { title: '夏普比率', key: 'sharpe_ratio', render: (row) => row.isGroup ? (row.best_sharpe > -Infinity ? row.best_sharpe.toFixed(2) : 'N/A') : (row.summary?.sharpe_ratio ? row.summary.sharpe_ratio.toFixed(2) : 'N/A') },
    { title: '最大回撤', key: 'max_drawdown', render: (row) => !row.isGroup && row.summary?.max_drawdown ? `${(row.summary.max_drawdown * 100).toFixed(2)}%` : 'N/A' },
    {
        title: '操作',
        key: 'actions',
        render(row) {
            return h(
                NButton,
                {
                    size: 'small',
                    onClick: () => row.isGroup ? showOptimizationReport(row.optimization_id) : showReportFromHistory(row.id),
                    disabled: row.status !== 'SUCCESS' && row.status !== 'COMPLETED'
                },
                { default: () => '查看报告' }
            );
        }
    }
];

const tradeHistoryColumns = [
  {
    title: '成交时间',
    key: 'date'
  },
  {
    title: '交易类型',
    key: 'type',
    render(row) {
      return h(
        NTag,
        { 
          size: 'small',
          type: row.type === 'buy' ? 'success' : 'error' 
        },
        { default: () => (row.type === 'buy' ? '买入' : '卖出') }
      )
    }
  },
  {
    title: '成交价格',
    key: 'price',
    render: (row) => row.price.toFixed(2)
  },
  {
    title: '成交数量',
    key: 'shares',
    render: (row) => row.shares.toFixed(4)
  }
];

const renderBacktestChart = (result) => {
  if (!backtestChartContainer.value) return;
  backtestChart = echarts.init(backtestChartContainer.value);

  const pnlData = (result.daily_pnl && result.daily_pnl.pnl) ? result.daily_pnl.pnl : [];
  const tradesData = (result.daily_pnl && result.daily_pnl.trades) ? result.daily_pnl.trades : [];

  const orderPoints = tradesData.map(trade => ({
    name: trade.type === 'buy' ? '买入' : '卖出',
    coord: [trade.date, trade.price],
    value: `${trade.type.toUpperCase()} @ ${trade.price.toFixed(2)}`,
    symbol: trade.type === 'buy' ? 'arrow' : 'pin',
    symbolSize: 15,
    itemStyle: {
      color: trade.type === 'buy' ? '#52c41a' : '#ff4d4f'
    }
  }));

  backtestChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: pnlData.map(d => d.date) },
    yAxis: { type: 'value', name: '权益', scale: true },
    series: [
      {
        name: '每日权益',
        type: 'line',
        data: pnlData.map(d => d.pnl),
        smooth: true,
        showSymbol: false,
        markPoint: {
          data: orderPoints
        }
      }
    ]
  });
};

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
    newStrategyData.template_name = 'empty';
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
  editStrategyData.content = '// Loading...';
  showEditModal.value = true;

  api.getStrategyScript(strategy.id).then(response => {
    editStrategyData.content = response.data.content || `// Code for ${strategy.name}`;
    nextTick(() => {
      if (editorContainer.value) {
        if (!monacoInstance) {
          monacoInstance = monaco.editor.create(editorContainer.value, {
            value: editStrategyData.content,
            language: 'python',
            theme: 'vs-dark'
          });
        } else {
          monacoInstance.setValue(editStrategyData.content);
        }
      }
    });
  }).catch(() => message.error('Failed to load strategy code.'));
}

async function handleUpdateStrategy() {
  if (!monacoInstance) return;
  const newContent = monacoInstance.getValue();
  try {
    await api.updateStrategy(editStrategyData.id, { script_content: newContent });
    message.success('策略代码保存成功');
    showEditModal.value = false;
  } catch (error) {
    message.error('代码保存失败');
  }
}

async function runStrategy(id) {
  try {
    await api.startStrategy(id);
    message.success('模拟交易已启动');
    fetchStrategies();
  }
  catch (error) {
    message.error('启动模拟交易失败');
  }
}

async function stopStrategy(id) {
  try {
    await api.stopStrategy(id);
    message.success('模拟交易已停止');
    dashboardStore.clearData();
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

function openBacktestModal(strategy) {
  backtestParams.strategy_id = strategy.id;
  backtestParams.start_date = new Date().setFullYear(new Date().getFullYear() - 1);
  backtestParams.end_date = Date.now();
  showBacktestModal.value = true;
}

async function handleRunBacktest() {
  try {
    dashboardStore.clearData();
    const backtestRequestParams = {
      symbol: backtestParams.symbol,
      duration: backtestParams.duration,
      start_dt: new Date(backtestParams.start_date).toISOString(),
      end_dt: new Date(backtestParams.end_date).toISOString(),
      commission_rate: backtestParams.commission_rate,
      slippage: backtestParams.slippage,
    };

    if (optimParams.value.length > 0) {
      const optimizationRequestParams = {
        ...backtestRequestParams,
        optim_params: optimParams.value,
      };
      await api.runOptimization(backtestParams.strategy_id, optimizationRequestParams);
      message.success('参数优化任务已启动！请稍后在历史报告中查看结果。');
      backtesting_ids.value.add(backtestParams.strategy_id);
      startPolling(backtestParams.strategy_id);
    } else {
        const { data } = await api.runBacktest(backtestParams.strategy_id, backtestRequestParams);
        message.info(`回测任务已启动 (ID: ${data.backtest_id})，等待结果...`);
        dashboardStore.addLog(`[${new Date().toLocaleTimeString()}] Backtest (ID: ${data.backtest_id}) started. Waiting for completion...`);
        backtesting_ids.value.add(backtestParams.strategy_id);
        startPolling(backtestParams.strategy_id);
    }

    optimParams.value = [];
    showBacktestModal.value = false;

  } catch (error) {
    const errorMsg = error.response?.data?.detail || '启动回测/优化失败';
    message.error(errorMsg);
    backtesting_ids.value.delete(backtestParams.strategy_id);
  }
}

watch(showBacktestModal, (isShown) => {
  if (!isShown) {
    optimParams.value = [];
  }
});

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
            startPolling(strategyId);
        } else if (!isAnyRunning && pollingInterval) {
            stopPolling();
            backtesting_ids.value.delete(strategyId);
            fetchStrategies(); // 优化完成后刷新策略状态
        }

    } catch (error) {
        message.error('加载历史报告失败');
        stopPolling();
    }
}

async function showReportFromHistory(backtestId) {
    try {
        dashboardStore.clearData();
        const { data } = await api.getBacktestReport(backtestId);
        dashboardStore.setBacktestResult(data);
        showHistoryModal.value = false;

    } catch (error) {
        message.error('加载报告详情失败');
    }
}

async function showOptimizationReport(optimizationId) {
  try {
    const { data } = await api.getOptimizationResults(optimizationId);
    optimizationResults.value = data;
    showHistoryModal.value = false;
    showOptimizationReportModal.value = true;
    nextTick(() => renderOptimizationChart(data));
  } catch (error) {
    message.error('加载优化报告失败');
  }
}

function renderOptimizationChart(results) {
  if (!optimizationChartContainer.value) return;
  optimizationChart = echarts.init(optimizationChartContainer.value);

  const params = results.map(r => r.summary.params);
  const paramNames = Object.keys(params[0]);
  const xAxisName = paramNames[0];
  const yAxisName = paramNames[1];

  const xData = [...new Set(params.map(p => p[xAxisName]))].sort((a, b) => a - b);
  const yData = [...new Set(params.map(p => p[yAxisName]))].sort((a, b) => a - b);

  const data = results.map(r => [
    r.summary.params[xAxisName],
    r.summary.params[yAxisName],
    r.summary.sharpe_ratio || 0
  ]);

  optimizationChart.setOption({
    tooltip: {
      position: 'top',
      formatter: function (params) {
        return `Sharpe: ${params.value[2].toFixed(2)}<br>${xAxisName}: ${params.value[0]}<br>${yAxisName}: ${params.value[1]}`;
      }
    },
    grid: {
      height: '80%',
      top: '10%'
    },
    xAxis: {
      type: 'category',
      data: xData,
      name: xAxisName
    },
    yAxis: {
      type: 'category',
      data: yData,
      name: yAxisName
    },
    visualMap: {
      min: Math.min(...data.map(d => d[2])),
      max: Math.max(...data.map(d => d[2])),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%'
    },
    series: [{
      name: 'Sharpe Ratio',
      type: 'heatmap',
      data: data,
      label: {
        show: true,
        formatter: function (params) {
          return params.value[2].toFixed(1);
        }
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  });
}

function startPolling(strategyId) {
  stopPolling();
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
  if (key === 'params' && typeof value === 'object' && value !== null) return JSON.stringify(value);
  if (typeof value !== 'number') return value;

  if (keyName.includes('ratio') || keyName.includes('rate') || keyName.includes('return') || keyName.includes('drawdown')) {
    return `${(value * 100).toFixed(2)}%`;
  }
  return value.toFixed(2);
};

const closeReportModal = () => {
  showBacktestReport.value = false;
  dashboardStore.setBacktestResult(null);
  if (backtestChart) {
    backtestChart.dispose();
    backtestChart = null;
  }
};

watch(backtestResult, (newResult) => {
  if (newResult) {
    backtesting_ids.value.delete(newResult.strategy_id);
    stopPolling();
    fetchStrategies();

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

onMounted(() => {
  dashboardStore.clearData();
  fetchStrategies();
  connectWebSocket();
});

onUnmounted(() => {
  disconnectWebSocket();
  stopPolling();
  backtestChart?.dispose();
  optimizationChart?.dispose();
  if (monacoInstance) monacoInstance.dispose();
});
</script>