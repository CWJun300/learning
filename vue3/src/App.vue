<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getHealth, listNotes } from '@/api/notes'

const route = useRoute()
const router = useRouter()

const keyword = ref('')
const health = ref(null)

const notesOpen = ref(false)
const navNotes = ref([])
const navLoading = ref(false)

async function loadNavNotes() {
  navLoading.value = true
  try {
    const data = await listNotes({ page: 1, size: 30 })
    navNotes.value = data.items
  } catch {
    // 侧边导航失败不影响主内容
  } finally {
    navLoading.value = false
  }
}

function toggleNotes() {
  notesOpen.value = !notesOpen.value
  if (notesOpen.value) loadNavNotes()
}

function submit() {
  const q = keyword.value.trim()
  if (!q) return
  router.push({ name: 'search', query: { q } })
}

function active(path) {
  return route.path === path
}

onMounted(async () => {
  try {
    health.value = await getHealth()
  } catch {
    health.value = null
  }
  loadNavNotes()
})

// 新增 / 删除 / 改名后路由会变化，借此刷新侧边列表
watch(
  () => route.fullPath,
  () => loadNavNotes(),
)
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

        <router-link class="nav-item" :class="{ active: active('/notes/new') }" to="/notes/new">
          新建
        </router-link>

        <div
          class="nav-item nav-toggle"
          :class="{ active: notesOpen }"
          @click="toggleNotes"
        >
          <span class="chev" :class="{ open: notesOpen }" />
          笔记
          <span class="nav-count">{{ navNotes.length }}</span>
        </div>

        <div v-if="notesOpen" class="nav-sub">
          <div v-if="navLoading" class="nav-loading">加载中…</div>
          <router-link
            v-for="item in navNotes"
            :key="item.id"
            class="nav-subitem"
            :class="{ active: active(`/notes/${item.id}`) }"
            :to="`/notes/${item.id}`"
            :title="item.title"
          >
            {{ item.title }}
          </router-link>
          <router-link v-if="!navLoading && !navNotes.length" class="nav-subitem nav-more" to="/notes/new">
            还没有笔记，去写一篇
          </router-link>
          <router-link v-if="navNotes.length" class="nav-subitem nav-more" to="/">
            查看全部
          </router-link>
        </div>

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
  height: 86px;
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
  height: calc(100vh - 86px);
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
  gap: 6px;
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

.nav-toggle {
  justify-content: flex-start;
}

.chev {
  width: 0;
  height: 0;
  border-left: 5px solid currentColor;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  transition: transform 0.18s;
  flex: 0 0 auto;
}

.chev.open {
  transform: rotate(90deg);
}

.nav-count {
  margin-left: auto;
  font-size: 12px;
  color: #a8abb2;
  font-weight: 400;
}

.nav-sub {
  display: flex;
  flex-direction: column;
  padding: 2px 0 6px 18px;
  max-height: 46vh;
  overflow-y: auto;
}

.nav-subitem {
  display: block;
  padding: 6px 10px;
  border-radius: 5px;
  font-size: 13px;
  color: #606266;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-subitem:hover {
  background: #f5f7fa;
  color: #409eff;
}

.nav-subitem.active {
  background: #ecf5ff;
  color: #409eff;
}

.nav-more {
  color: #a8abb2;
  font-size: 12px;
}

.nav-loading {
  font-size: 12px;
  color: #c0c4cc;
  padding: 6px 10px;
}

.nav-footer {
  margin-top: auto;
  padding: 12px 10px 4px;
}

.app-main {
  padding: 20px 24px 40px;
  overflow-y: auto;
}

/* Element Plus 的 el-aside 默认有背景色，这里覆盖 */
.el-aside.nav-aside {
  overflow: visible;
}
</style>
