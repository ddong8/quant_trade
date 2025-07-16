<template>
  <n-config-provider :theme="darkTheme">
    <n-spin :show="isLoading">
      <n-message-provider>
        <n-dialog-provider>
          <router-view />
        </n-dialog-provider>
      </n-message-provider>
      <n-global-style />
    </n-spin>
  </n-config-provider>
</template>

<script setup>
import { NConfigProvider, NMessageProvider, NDialogProvider, NGlobalStyle, NSpin, darkTheme } from 'naive-ui';
import { useAppStore } from '@/stores/app';
import { storeToRefs } from 'pinia';

const appStore = useAppStore();
const { isLoading } = storeToRefs(appStore);
</script>