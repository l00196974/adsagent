<template>
  <el-config-provider :locale="locale">
    <el-container>
      <el-header>
        <div class="logo">广告知识图谱系统</div>
        <el-menu mode="horizontal" :router="true" :default-active="$route.path">
          <el-menu-item index="/modeling">基础建模</el-menu-item>
          <el-menu-item index="/events">事件抽象</el-menu-item>
          <el-menu-item index="/mining">高频子序列挖掘</el-menu-item>
          <el-sub-menu index="/causal-graph">
            <template #title>事理图谱</template>
            <el-menu-item index="/causal-graph/generate">生成图谱</el-menu-item>
            <el-menu-item index="/causal-graph/view">查看图谱</el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/qa">智能问答</el-menu-item>
        </el-menu>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>

    <!-- 全局LLM日志面板 -->
    <LLMLogPanel />
  </el-config-provider>
</template>

<script setup>
import { ref } from 'vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import LLMLogPanel from './components/LLMLogPanel.vue'

const locale = ref(zhCn)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.el-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.logo {
  font-size: 20px;
  font-weight: bold;
  color: #409EFF;
}

.el-main {
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.el-card {
  margin-bottom: 20px;
}
</style>
