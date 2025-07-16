// frontend/src/stores/app.js
import { defineStore } from 'pinia';

export const useAppStore = defineStore('app', {
  state: () => ({
    isLoading: false,
  }),
  actions: {
    setLoading(status) {
      this.isLoading = status;
    },
  },
});