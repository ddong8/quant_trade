// frontend/src/stores/auth.js

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '@/router'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(null); // 初始化为 null
  const user = ref(null);

  const isAuthenticated = computed(() => !!token.value);

  function setToken(newToken) {
    token.value = newToken;
    if (newToken) {
      localStorage.setItem('token', newToken);
      api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    } else {
      localStorage.removeItem('token');
      delete api.defaults.headers.common['Authorization'];
    }
  }

  async function login(credentials) {
    // ... login 函数保持不变 ...
    try {
      const formData = new URLSearchParams();
      formData.append('username', credentials.username);
      formData.append('password', credentials.password);
      
      const { data } = await api.post('/login/access-token', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      
      setToken(data.access_token);
      router.push({ name: 'dashboard' });
    } catch (error) {
      console.error('Login failed:', error);
      logout(); 
      throw error;
    }
  }

  function logout() {
    setToken(null);
    user.value = null;
    router.push({ name: 'login' });
  }

  function checkAuthOnLoad() {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
    }
  }
  
  // 不再在这里自动调用 checkAuthOnLoad()

  return { token, user, isAuthenticated, login, logout, checkAuthOnLoad }; // 导出 checkAuthOnLoad
})