<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { deleteNote, getNote, getRelated } from '@/api/notes'
import MarkdownView from '@/components/MarkdownView.vue'

const props = defineProps({
  id: { type: String, required: true },
})

const router = useRouter()
const note = ref(null)
const related = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    note.value = await getNote(props.id)
    related.value = await getRelated(props.id, 5)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function remove() {
  try {
    await ElMessageBox.confirm('删除后不可恢复，确定删除这篇笔记？', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteNote(props.id)
    ElMessage.success('已删除')
    router.push('/')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : ''
}

onMounted(load)
</script>

<template>
  <el-skeleton v-if="loading" :rows="6" animated />

  <el-empty v-else-if="!note" description="笔记不存在" />

  <div v-else class="detail">
    <article class="article">
      <div class="article-head">
        <h1 class="article-title">{{ note.title }}</h1>
        <div class="article-actions">
          <el-button @click="router.push(`/notes/${note.id}/edit`)">编辑</el-button>
          <el-button type="danger" plain @click="remove">删除</el-button>
        </div>
      </div>

      <div class="article-meta">
        <el-tag v-for="tag in note.tags" :key="tag.id" size="small" type="info">
          {{ tag.name }}
        </el-tag>
        <span class="meta-text">创建于 {{ formatDate(note.created_at) }}</span>
        <span class="meta-text">更新于 {{ formatDate(note.updated_at) }}</span>
      </div>

      <el-divider />

      <MarkdownView :source="note.content" />
    </article>

    <aside class="related">
      <el-card shadow="never">
        <template #header>相似笔记</template>
        <el-empty v-if="!related.length" description="暂无相似内容" :image-size="60" />
        <ul v-else class="related-list">
          <li
            v-for="item in related"
            :key="item.id"
            class="related-item"
            @click="router.push(`/notes/${item.id}`)"
          >
            <div class="related-title">{{ item.title }}</div>
            <div class="related-score">相似度 {{ (item.score * 100).toFixed(0) }}%</div>
          </li>
        </ul>
      </el-card>
    </aside>
  </div>
</template>

<style scoped>
.detail {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 20px;
  align-items: flex-start;
}
.article {
  min-width: 0;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 20px 24px;
}
.article-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.article-title {
  margin: 0;
  font-size: 22px;
  line-height: 1.4;
}
.article-actions {
  white-space: nowrap;
}
.article-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.meta-text {
  font-size: 12px;
  color: #c0c4cc;
}
.related-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.related-item {
  padding: 8px 4px;
  border-bottom: 1px dashed #ebeef5;
  cursor: pointer;
}
.related-item:last-child {
  border-bottom: none;
}
.related-item:hover .related-title {
  color: #409eff;
}
.related-title {
  font-size: 13px;
  line-height: 1.5;
}
.related-score {
  font-size: 11px;
  color: #c0c4cc;
}
</style>
