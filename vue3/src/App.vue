<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getHealth } from '@/api/notes'

const route = useRoute()
const router = useRouter()

const keyword = ref('')
const health = ref(null)

/** 「笔记」在列表页和详情页时都算选中 */
const notesActive = computed(
  () => route.path === '/' || (route.path.startsWith('/notes/') && route.path !== '/notes/new'),
)

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
      <div class="brand" @click="router.push('/')">个人知识库</div>

      <div class="search-wrap">
        <div class="search-bar">
          <el-input
            v-model="keyword"
            class="search-input"
            placeholder="搜索笔记…支持 +必含词、短语、#标签"
            clearable
            @keyup.enter="submit"
          />
          <el-button type="primary" class="search-btn" @click="submit">搜索</el-button>
        </div>
      </div>

      <div class="header-right" />
    </el-header>

    <el-container class="app-body">
      <el-aside width="210px" class="nav-aside">
        <div class="nav-title">导航</div>

        <router-link class="nav-item" :class="{ active: route.path === '/notes/new' }" to="/notes/new">
          新建
        </router-link>

        <router-link class="nav-item" :class="{ active: route.path === '/import' }" to="/import">
          导入
        </router-link>

        <router-link class="nav-item" :class="{ active: notesActive }" to="/">
          笔记
        </router-link>

        <div class="nav-footer">
          <el-tag v-if="health" :type="health.db === 'ok' ? 'success' : 'warning'" size="small">
            {{ health.db === 'ok' ? `已连接 · ${health.index_docs} 篇` : '数据库未连接' }}
          </el-tag>
        </div>
      </el-aside>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
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
  height: 100vh;
}

/* ---------- 顶栏：品牌在左，大搜索框居中 ---------- */
.app-header {
  display: grid;
  grid-template-columns: 210px 1fr 210px;
  align-items: center;
  height: 96px;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.brand {
  justify-self: start;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #303133;
  cursor: pointer;
  white-space: nowrap;
}

.brand:hover {
  color: #409eff;
}

.search-wrap {
  display: flex;
  justify-content: center;
  /* 搜索框整体比品牌略有下沉，避免和标题挤在同一水平线上 */
  padding-top: 12px;
}

.search-bar {
  display: flex;
  width: 100%;
  max-width: 760px;
}

.search-input .el-input__wrapper {
  height: 50px;
  font-size: 16px;
  border-radius: 25px 0 0 25px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

.search-input .el-input__inner {
  padding-left: 18px;
}

.search-btn {
  height: 50px;
  padding: 0 30px;
  font-size: 16px;
  border-radius: 0 25px 25px 0;
}

.header-right {
  justify-self: end;
}

/* ---------- 主体 ---------- */
.app-body {
  height: calc(100vh - 96px);
}

.nav-aside {
  background: #fff;
  border-right: 1px solid #ebeef5;
  padding: 16px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.nav-title {
  font-size: 12px;
  color: #a8abb2;
  padding: 4px 10px 8px;
  letter-spacing: 1px;
}

.nav-item {
  display: flex;
  align-items: center;
  height: 38px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 14px;
  color: #303133;
  text-decoration: none;
  cursor: pointer;
  user-select: none;
}

.nav-item:hover {
  background: #f5f7fa;
}

.nav-item.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 600;
}

.nav-footer {
  margin-top: auto;
  padding: 12px 10px 4px;
}

.app-main {
  padding: 20px 24px 40px;
  overflow-y: auto;
}
</style>
