<script setup>
import { ref, onMounted } from 'vue'
import http from './api/http.js'

const health = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    health.value = await http.get('/health')
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand">📚 个人知识库</div>
      <div class="status">
        <el-tag v-if="health" :type="health.db === 'ok' ? 'success' : 'danger'" size="small">
          后端 {{ health.status }} / 数据库 {{ health.db }} / 索引 {{ health.index_docs }} 篇
        </el-tag>
        <el-tag v-else-if="error" type="danger" size="small">连不上后端：{{ error }}</el-tag>
        <el-tag v-else type="info" size="small">连接中…</el-tag>
      </div>
    </el-header>

    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
}

.app-shell {
  height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #ebeef5;
}

.brand {
  font-size: 18px;
  font-weight: 600;
}

.status {
  font-size: 12px;
}
</style>
