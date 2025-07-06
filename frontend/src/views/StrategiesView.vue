<template>
  <n-space vertical :size="24">
    <!-- 创建策略 -->
    <n-h1>创建新策略</n-h1>
    <n-card title="编写策略代码">
      <n-form @submit.prevent="saveStrategy">
        <n-form-item label="策略名称">
          <n-input v-model:value="newStrategy.name" placeholder="为你的策略起个名字" />
        </n-form-item>
        <n-form-item label="策略描述">
          <n-input v-model:value="newStrategy.description" placeholder="简单描述一下策略的用途" />
        </n-form-item>
        <n-form-item label="策略代码 (Python)">
          <n-input
            v-model:value="newStrategy.script_content"
            type="textarea"
            placeholder="在这里编写你的Python策略代码..."
            :autosize="{ minRows: 10, maxRows: 20 }"
            style="font-family: 'Courier New', Courier, monospace;"
          />
        </n-form-item>
        <n-form-item>
          <n-button type="primary" attr-type="submit" :loading="saving">保存策略</n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <!-- 策略管理 -->
    <n-h1>策略管理</n-h1>
    <n-spin :show="loading">
      <n-grid :cols="3" :x-gap="24" :y-gap="24">
        <n-gi v-for="s in strategies" :key="s.id">
          <n-card :title="s.name" hoverable>
            <template #header-extra>
              <n-tag :type="s.status === 'running' ? 'success' : 'default'" round>
                {{ statusMap[s.status] || '未知' }}
              </n-tag>
            </template>
            <p>{{ s.description }}</p>
            <small>脚本: {{ s.script_path }}</small>
            <template #action>
              <n-space justify="end">
                <n-button size="small" @click="openEditModal(s)" :disabled="s.status === 'running'">编辑</n-button>
                <n-button 
                  size="small"
                  type="primary" 
                  ghost 
                  @click="startStrategy(s.id)"
                  :disabled="s.status === 'running'"
                  :loading="s.loading"
                >启动</n-button>
                <n-button 
                  size="small"
                  type="error" 
                  ghost
                  @click="stopStrategy(s.id)"
                  :disabled="s.status !== 'running'"
                  :loading="s.loading"
                >停止</n-button>
                <n-button
                  size="small"
                  type="error"
                  @click="handleDeleteClick(s.id)"
                  :disabled="s.status === 'running'"
                >删除</n-button>
              </n-space>
            </template>
          </n-card>
        </n-gi>
      </n-grid>
      <n-empty v-if="!strategies.length" description="还没有创建任何策略" />
    </n-spin>

    <!-- 编辑策略模态框 -->
    <n-modal v-model:show="showEditModal" preset="card" style="width: 600px" title="编辑策略">
      <n-form @submit.prevent="updateStrategy">
        <n-form-item label="策略名称">
          <n-input v-model:value="editingStrategy.name" />
        </n-form-item>
        <n-form-item label="策略描述">
          <n-input v-model:value="editingStrategy.description" />
        </n-form-item>
        <n-form-item label="策略代码">
          <n-input
            v-model:value="editingStrategy.script_content"
            type="textarea"
            :autosize="{ minRows: 15, maxRows: 25 }"
            style="font-family: 'Courier New', Courier, monospace;"
          />
        </n-form-item>
        <n-space justify="end">
          <n-button @click="showEditModal = false">取消</n-button>
          <n-button type="primary" attr-type="submit" :loading="saving">保存修改</n-button>
        </n-space>
      </n-form>
    </n-modal>

    <!-- 全局日志面板 -->
    <n-h1>全局实时日志</n-h1>
    <n-card title="Log Stream">
      <n-button size="small" @click="dashboardStore.clearData()" style="margin-bottom: 12px;">清空日志</n-button>
      <n-log
        :log="logs.join('\n')"
        :rows="15"
        style="font-family: 'Courier New', Courier, monospace; font-size: 12px;"
      />
    </n-card>

  </n-space>
</template>

<script setup>
import { ref, onMounted, reactive, onBeforeUnmount } from 'vue';
import { 
  NSpace, NGrid, NGi, NCard, NTag, NButton, useMessage, NH1, NSpin, 
  NForm, NFormItem, NInput, NEmpty, NModal, useDialog, NLog
} from 'naive-ui';
import api from '@/services/api';
import { useDashboardStore } from '@/stores/dashboard';
import { connectWebSocket, disconnectWebSocket } from '@/services/websocket';
import { storeToRefs } from 'pinia';

const message = useMessage();
const dialog = useDialog();
const dashboardStore = useDashboardStore();
const { logs } = storeToRefs(dashboardStore);

const loading = ref(true);
const saving = ref(false);
const strategies = ref([]);

// For creating new strategy
const newStrategy = reactive({
  name: '',
  description: '',
  script_content: ''
});

// For editing existing strategy
const showEditModal = ref(false);
const editingStrategy = ref(null);

const statusMap = {
  stopped: '已停止',
  running: '运行中',
  error: '错误'
};

const fetchStrategies = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/strategies/');
    strategies.value = data.map(s => ({ ...s, loading: false }));
  } catch (error) {
    message.error("获取策略列表失败");
  } finally {
    loading.value = false;
  }
};

const saveStrategy = async () => {
  if (!newStrategy.name || !newStrategy.script_content) {
    message.warning("策略名称和代码内容不能为空");
    return;
  }
  saving.value = true;
  try {
    await api.post('/strategies/', newStrategy);
    message.success("策略保存成功");
    newStrategy.name = '';
    newStrategy.description = '';
    newStrategy.script_content = '';
    fetchStrategies();
  } catch (error) {
    message.error("保存策略失败");
  } finally {
    saving.value = false;
  }
};

const openEditModal = async (strategy) => {
  editingStrategy.value = { ...strategy, script_content: '加载中...' };
  showEditModal.value = true;
  try {
    const { data } = await api.get(`/strategies/${strategy.id}/script`);
    editingStrategy.value.script_content = data.script_content;
  } catch (error) {
    message.error("加载策略代码失败");
    editingStrategy.value.script_content = "# 加载失败，请重试";
  }
};

const updateStrategy = async () => {
  if (!editingStrategy.value) return;
  saving.value = true;
  try {
    await api.put(`/strategies/${editingStrategy.value.id}`, {
      name: editingStrategy.value.name,
      description: editingStrategy.value.description,
      script_content: editingStrategy.value.script_content,
    });
    message.success("策略更新成功");
    showEditModal.value = false;
    fetchStrategies();
  } catch (error) {
    message.error(error.response?.data?.detail || "更新策略失败");
  } finally {
    saving.value = false;
  }
};

const handleDeleteClick = (id) => {
  dialog.warning({
    title: '确认删除',
    content: '您确定要删除这个策略吗？此操作不可恢复。',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.delete(`/strategies/${id}`);
        message.success('策略删除成功');
        fetchStrategies();
      } catch (error) {
        message.error(error.response?.data?.detail || '删除策略失败');
      }
    },
  });
};

const updateStrategyState = (id, isLoading, newStatus = null) => {
    const index = strategies.value.findIndex(s => s.id === id);
    if (index !== -1) {
        strategies.value[index].loading = isLoading;
        if (newStatus) {
            strategies.value[index].status = newStatus;
        }
    }
}

const startStrategy = async (id) => {
  updateStrategyState(id, true);
  try {
    const { data } = await api.post(`/strategies/${id}/start`);
    message.success("策略启动成功");
    updateStrategyState(id, false, data.status);
  } catch (error) {
    message.error(error.response?.data?.detail || "启动策略失败");
    updateStrategyState(id, false);
  }
};

const stopStrategy = async (id) => {
  updateStrategyState(id, true);
  try {
    const { data } = await api.post(`/strategies/${id}/stop`);
    message.success("策略停止成功");
    updateStrategyState(id, false, data.status);
  } catch (error) {
    message.error(error.response?.data?.detail || "停止策略失败");
    updateStrategyState(id, false);
  }
};

onMounted(() => {
  fetchStrategies();
  connectWebSocket(
    () => message.success('WebSocket 已连接'),
    () => message.warning('WebSocket 已断开'),
    (err) => message.error('WebSocket 连接错误')
  );
});

onBeforeUnmount(() => {
  disconnectWebSocket();
});
</script>


