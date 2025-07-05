<template>
  <div class="login-container">
    <n-card class="login-card" title="量化交易系统登录">
      <n-form @submit.prevent="handleLogin">
        <n-form-item-row label="用户名">
          <n-input v-model:value="username" placeholder="输入任意用户名" />
        </n-form-item-row>
        <n-form-item-row label="密码">
          <n-input type="password" v-model:value="password" placeholder="输入任意密码" show-password-on="click" />
        </n-form-item-row>
        <n-button type="primary" block strong attr-type="submit" :loading="loading">
          登 录
        </n-button>
      </n-form>
    </n-card>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { NCard, NForm, NFormItemRow, NInput, NButton, useMessage } from 'naive-ui';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();
const message = useMessage();
const username = ref('demo');
const password = ref('demo');
const loading = ref(false);

const handleLogin = async () => {
  loading.value = true;
  try {
    await authStore.login({ username: username.value, password: password.value });
    message.success('登录成功');
  } catch (error) {
    message.error('登录失败，请重试');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #101014;
}
.login-card {
  width: 400px;
}
</style>