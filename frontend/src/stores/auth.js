// frontend/src/stores/auth.js

import { defineStore } from 'pinia';
import { ref } from 'vue';
import router from '@/router'; // <--- 直接从router模块导入实例
import api from '@/services/api';

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token'));
  
  // 不在这里调用 useRouter()
  // const router = useRouter(); 

function setToken(newToken) {
  token.value = newToken;
  if (newToken) {
    localStorage.setItem('token', newToken); // <-- 确保这行存在
  } else {
    localStorage.removeItem('token');
  }
}

  async function login(credentials) {
    try {
      const response = await api.login(credentials);
      const accessToken = response.data.access_token;
      setToken(accessToken);

      // 在这里进行跳转
      await router.push({ name: 'dashboard' });
      
    } catch (error) {
      console.error('Login failed:', error);
      throw new Error('Login failed');
    }
  }

  function logout() {
    setToken(null);
    // 在这里进行跳转
    router.push({ name: 'login' });
  }

  return {
    token,
    login,
    logout,
  };
});