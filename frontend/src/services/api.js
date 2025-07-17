// frontend/src/services/api.js

import axios from 'axios';

// --- apiClient for most API calls ---
const apiClient = axios.create({
  baseURL: '/api/v1',
});

// Add a request interceptor to apiClient
apiClient.interceptors.request.use(
  (config) => {
    // Directly get the token from localStorage
    const token = localStorage.getItem('token'); 
    
    if (token) {
      // If token exists, add it to the Authorization header
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // Do something with request error
    return Promise.reject(error);
  }
);


// --- authApiClient for login ---
// This is used ONLY for the login call, which has a different path and content type
const authApiClient = axios.create({
    baseURL: '/',
});

export default {
    // --- API methods using apiClient (will have token automatically) ---
    getStrategies() { return apiClient.get('/strategies/'); },
    createStrategy(data) { return apiClient.post('/strategies/', data); },
    updateStrategy(id, data) { return apiClient.put(`/strategies/${id}`, data); },
    getStrategyScript(id) { return apiClient.get(`/strategies/${id}/script`); },
    deleteStrategy(id) { return apiClient.delete(`/strategies/${id}`); },
    startStrategy(id) { return apiClient.post(`/strategies/${id}/start`); },
    stopStrategy(id) { return apiClient.post(`/strategies/${id}/stop`); },
    runBacktest(strategyId, params) { return apiClient.post(`/backtests/run/${strategyId}`, params); },
    runOptimization(strategyId, params) { return apiClient.post(`/backtests/optimize/${strategyId}`, params); },
    getBacktestHistory(strategyId) { return apiClient.get(`/backtests/history/${strategyId}`); },
    getBacktestReport(backtestId) { return apiClient.get(`/backtests/${backtestId}`); },
    getOptimizationResults(optimizationId) { return apiClient.get(`/backtests/optimization/${optimizationId}`); },

    // --- Login method using apiClient ---
    login(credentials) {
        const params = new URLSearchParams();
        params.append('username', credentials.username);
        params.append('password', credentials.password);
        
        return apiClient.post('/login/access-token', params, {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
        });
    }
};