<template>
  <n-layout style="height: 100vh">
    <n-layout-header style="height: 64px; padding: 0 24px;" bordered>
      <div class="header-content">
        <div class="logo">🚀 Quant System</div>
        <n-button text @click="handleLogout">
          <template #icon><n-icon :component="LogoutIcon" /></template>
          退出登录
        </n-button>
      </div>
    </n-layout-header>
    <n-layout has-sider position="absolute" style="top: 64px; bottom: 0">
      <n-layout-sider
        bordered
        collapse-mode="width"
        :collapsed-width="64"
        :width="240"
        show-trigger
      >
        <n-menu
          :options="menuOptions"
          :value="activeKey"
          @update:value="handleMenuSelect"
        />
      </n-layout-sider>
      <n-layout content-style="padding: 24px;" :native-scrollbar="false">
        <router-view />
      </n-layout>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { h, ref, computed } from 'vue';
import { NLayout, NLayoutHeader, NLayoutSider, NMenu, NIcon, NButton } from 'naive-ui';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import {
  DesktopOutline as DashboardIcon,
  CodeSlashOutline as StrategyIcon,
  LogOutOutline as LogoutIcon
} from '@vicons/ionicons5';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const renderIcon = (icon) => () => h(NIcon, null, { default: () => h(icon) });

const menuOptions = [
  { label: () => h(RouterLink, { to: { name: 'dashboard' } }, { default: () => '仪表盘' }), key: 'dashboard', icon: renderIcon(DashboardIcon) },
  { label: () => h(RouterLink, { to: { name: 'strategies' } }, { default: () => '策略管理' }), key: 'strategies', icon: renderIcon(StrategyIcon) },
];

const activeKey = computed(() => route.name);

const handleMenuSelect = (key, item) => {
  router.push({ name: key });
};

const handleLogout = () => {
  authStore.logout();
};
</script>

<style scoped>
.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}
.logo {
  font-size: 20px;
  font-weight: bold;
}
</style>