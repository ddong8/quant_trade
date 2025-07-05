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
const username = ref('admin'); // 后端硬编码的用户名
const password = ref('password'); // 后端硬编码的密码
const loading = ref(false);

const handleLogin = async () => {
  if (!username.value || !password.value) {
    message.error("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    await authStore.login({ username: username.value, password: password.value });
    // 登录成功后会自动跳转，不需要在这里 message.success
  } catch (error) {
    message.error('登录失败：用户名或密码错误');
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