import axios from 'axios';
import { useAuthStore } from '@/stores/auth';
import router from '@/router'; // 引入 router

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the token
apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();
    const token = authStore.token;
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && [401, 403].includes(error.response.status)) {
      const authStore = useAuthStore();
      authStore.logout(); // 清除 token 和用户信息
      router.push('/login'); // 重定向到登录页
    }
    return Promise.reject(error);
  }
);


export default {
  // Auth
  login(credentials) {
    const params = new URLSearchParams();
    params.append('username', credentials.username);
    params.append('password', credentials.password);
    return apiClient.post('/login/access-token', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },

  // Strategies
  get(path) {
    return apiClient.get(path);
  },
  post(path, data) {
    return apiClient.post(path, data);
  },
  put(path, data) {
    return apiClient.put(path, data);
  },
  delete(path) {
    return apiClient.delete(path);
  },

  // Backtesting
  runBacktest(strategyId, params) {
    return apiClient.post(`/strategies/${strategyId}/backtest`, params);
  },
  getBacktestHistoryForStrategy(strategyId) {
    return apiClient.get(`/backtests/history/${strategyId}`);
  },
  getBacktestReport(backtestId) {
    return apiClient.get(`/backtests/${backtestId}`);
  }
};
