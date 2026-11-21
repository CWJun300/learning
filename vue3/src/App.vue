<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getHealth } from '@/api/notes'

const router = useRouter()
const keyword = ref('')
const health = ref(null)

function submit() {
  const q = keyword.value.trim()
  if (!q) return
  router.push({ name: 'search', query: { q } })
}

onMounted(async () => {
  try {
    health.value = await getHealth()
  } catch {
    health.value = null
  }
})
</script>

<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand" @click="router.push('/')">📚 个人知识库</div>

      <el-input
        v-model="keyword"
        class="search-box"
        placeholder="搜索笔记…（支持 +必含词 / 短语 / #标签）"
        clearable
        @keyup.enter="submit"
      >
        <template #append>
          <el-button @click="submit">搜索</el-button>
        </template>
      </el-input>

      <div class="header-right">
        <el-button type="primary" @click="router.push('/notes/new')">新建</el-button>
        <el-tag v-if="health" :type="health.db === 'ok' ? 'success' : 'warning'" size="small">
          {{ health.db === 'ok' ? `已连接 · ${health.index_docs} 篇` : '数据库未连接' }}
        </el-tag>
      </div>
    </el-header>

    <el-main class="app-main">
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

body {
  background: #f5f7fa;
}

.app-shell {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.brand {
  font-size: 17px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
}

.search-box {
  max-width: 520px;
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.app-main {
  padding: 20px 24px 40px;
}
</style>
