<template>
  <n-space vertical :size="24">
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
                <n-button 
                  type="primary" 
                  ghost 
                  @click="startStrategy(s.id)"
                  :disabled="s.status === 'running'"
                  :loading="s.loading"
                >启动</n-button>
                <n-button 
                  type="error" 
                  ghost
                  @click="stopStrategy(s.id)"
                  :disabled="s.status !== 'running'"
                  :loading="s.loading"
                >停止</n-button>
              </n-space>
            </template>
          </n-card>
        </n-gi>
      </n-grid>
    </n-spin>
  </n-space>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { NSpace, NGrid, NGi, NCard, NTag, NButton, useMessage, NH1, NSpin } from 'naive-ui';
import api from '@/services/api';

const message = useMessage();
const loading = ref(true);
const strategies = ref([]);

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
    await api.post(`/strategies/${id}/start`);
    message.success("策略启动成功");
    updateStrategyState(id, false, 'running');
  } catch (error) {
    message.error("启动策略失败");
    updateStrategyState(id, false);
  }
};

const stopStrategy = async (id) => {
  updateStrategyState(id, true);
  try {
    await api.post(`/strategies/${id}/stop`);
    message.success("策略停止成功");
    updateStrategyState(id, false, 'stopped');
  } catch (error) {
    message.error("停止策略失败");
    updateStrategyState(id, false);
  }
};

onMounted(fetchStrategies);
</script>