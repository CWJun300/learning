<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DOMPurify from 'dompurify'
import { ElMessage } from 'element-plus'

import { searchNotes } from '@/api/notes'

const route = useRoute()
const router = useRouter()

const keyword = ref('')
const results = ref([])
const total = ref(0)
const page = ref(1)
const size = 10
const loading = ref(false)
const elapsed = ref(0)

async function runSearch() {
  const q = keyword.value.trim()
  if (!q) {
    results.value = []
    total.value = 0
    return
  }
  loading.value = true
  const started = performance.now()
  try {
    const data = await searchNotes({ q, page: page.value, size })
    results.value = data.items
    total.value = data.total
    elapsed.value = Math.round(performance.now() - started)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

function submit() {
  page.value = 1
  router.replace({ name: 'search', query: { q: keyword.value } })
  runSearch()
}

function changePage(next) {
  page.value = next
  runSearch()
}

/** 后端返回的 snippet 已做 HTML 转义并插入 <mark>，这里再过一遍 DOMPurify */
function safeSnippet(html) {
  return DOMPurify.sanitize(html || '')
}

watch(
  () => route.query.q,
  (q) => {
    const next = q || ''
    if (next !== keyword.value) {
      keyword.value = next
      runSearch()
    }
  },
)

onMounted(() => {
  keyword.value = route.query.q || ''
  if (keyword.value) runSearch()
})
</script>

<template>
  <div class="search-page">
    <el-input
      v-model="keyword"
      size="large"
      placeholder="输入关键词，支持 +必含词、短语、#标签"
      clearable
      @keyup.enter="submit"
    >
      <template #append>
        <el-button @click="submit">搜索</el-button>
      </template>
    </el-input>

    <div class="summary">
      <template v-if="keyword && !loading">
        共 <b>{{ total }}</b> 条结果，耗时 {{ elapsed }} ms
      </template>
    </div>

    <el-skeleton v-if="loading" :rows="4" animated />

    <el-empty v-else-if="!keyword" description="输入关键词开始搜索" />

    <el-empty v-else-if="!results.length" description="没有找到匹配的笔记" />

    <div v-else class="result-list">
      <div
        v-for="item in results"
        :key="item.id"
        class="result-item"
        @click="router.push(`/notes/${item.id}`)"
      >
        <div class="result-head">
          <span class="result-title">{{ item.title }}</span>
          <span class="result-score">{{ item.score.toFixed(2) }}</span>
        </div>
        <!-- 已由 DOMPurify 净化，只保留 <mark> 等安全标签 -->
        <div class="result-snippet" v-html="safeSnippet(item.snippet)" />
        <div class="result-tags">
          <el-tag v-for="tag in item.tags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
        </div>
      </div>

      <el-pagination
        v-if="total > size"
        class="pager"
        background
        layout="prev, pager, next, total"
        :total="total"
        :page-size="size"
        :current-page="page"
        @current-change="changePage"
      />
    </div>
  </div>
</template>

<style scoped>
.search-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.summary {
  font-size: 12px;
  color: #909399;
  min-height: 18px;
}
.result-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.result-item {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px 16px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.result-item:hover {
  border-color: #409eff;
}
.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.result-title {
  font-size: 15px;
  font-weight: 600;
}
.result-score {
  font-size: 11px;
  color: #c0c4cc;
}
.result-snippet {
  margin: 6px 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
}
.result-snippet :deep(mark) {
  background: #fff3cd;
  color: #d48806;
  padding: 0 2px;
  border-radius: 2px;
}
.result-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.pager {
  justify-content: center;
  margin-top: 8px;
}
</style>
