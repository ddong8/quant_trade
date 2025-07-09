<template>
  <div style="padding: 24px;">
    <n-h1>仪表盘</n-h1>
    <n-p>
      所有功能已集成到“策略”页面。
    </n-p>
    <n-button type="primary" @click="$router.push('/strategies')">
      前往策略页面
    </n-button>
  </div>
</template>

<script setup>
import { NH1, NP, NButton } from 'naive-ui';
</script>
