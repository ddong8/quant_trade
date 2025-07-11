import axios from 'axios';
import { useAuthStore } from '@/stores/auth';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
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
  getBacktestHistory(strategyId) {
    return apiClient.get(`/strategies/${strategyId}/backtests`);
  },
  getBacktestReport(backtestId) {
    return apiClient.get(`/backtests/${backtestId}`);
  }
};
