<template>
  <el-config-provider :locale="locale">
    <el-container>
      <el-header>
        <div class="logo">广告知识图谱系统</div>
        <el-menu mode="horizontal" :router="true" :default-active="$route.path">
          <el-menu-item index="/">数据概览</el-menu-item>
          <el-menu-item index="/modeling">基础建模</el-menu-item>
          <el-menu-item index="/import">数据导入</el-menu-item>
          <el-menu-item index="/graph">图谱可视化</el-menu-item>
          <el-menu-item index="/qa">智能问答</el-menu-item>
        </el-menu>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-config-provider>
</template>

<script setup>
import { ref } from 'vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

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
