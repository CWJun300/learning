<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { deleteNote, getLinks, getNote, getRelated } from '@/api/notes'
import { topicPracticeRoute } from '@/api/study'
import MarkdownView from '@/components/MarkdownView.vue'
import CardComposer from '@/components/CardComposer.vue'
import TopicReadingBar from '@/components/TopicReadingBar.vue'

const props = defineProps({
  id: { type: String, required: true },
})

const router = useRouter()
const route = useRoute()
const excerpt = ref('')
const composing = ref(false)
const readingTopic = ref(null)

function captureSelection(event) {
  const selection = window.getSelection()
  excerpt.value = selection?.rangeCount && event.currentTarget.contains(selection.getRangeAt(0).commonAncestorContainer)
    ? selection.toString().trim() : ''
}
const note = ref(null)
const related = ref([])
const links = ref({ outgoing: [], incoming: [] })
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    note.value = await getNote(props.id)
    const [matches, references] = await Promise.all([getRelated(props.id, 5), getLinks(props.id)])
    related.value = matches
    links.value = references
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function remove() {
  try {
    await ElMessageBox.confirm('可在回收站恢复正文、标签和引用。', '移入回收站？', {
      type: 'warning',
      confirmButtonText: '移入回收站',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteNote(props.id)
    ElMessage.success('已移入回收站')
    router.push('/notes')
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
      <TopicReadingBar v-if="route.query.topic" :key="route.query.topic"
        :topic-id="String(route.query.topic)" :note-id="note.id" @ready="readingTopic = $event" />
      <div class="article-head">
        <h1 class="article-title">{{ note.title }}</h1>
        <div class="article-actions">
          <el-button @mousedown.prevent @click="composing = true">制作自测题</el-button>
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

      <div @mouseup="captureSelection" @keyup="captureSelection" @touchend="captureSelection">
        <MarkdownView :source="note.content" />
      </div>
      <footer v-if="readingTopic?.card_count && String(readingTopic.id) === route.query.topic" class="practice-footer">
        <router-link :to="topicPracticeRoute(readingTopic.id)">练习本专题 · {{ readingTopic.card_count }} 题 →</router-link>
      </footer>
      <CardComposer v-if="composing" :note-id="note.id" :excerpt="excerpt" @close="composing = false" />
    </article>

    <aside class="related">
      <el-card v-for="(label, key) in { outgoing: '本文引用', incoming: '被以下笔记引用' }" :key="key" shadow="never">
        <template #header>{{ label }} · {{ links[key].length }}</template>
        <ul v-if="links[key].length" class="related-list">
          <li v-for="item in links[key]" :key="item.id" class="related-item">
            <router-link :to="'/notes/' + item.id">{{ item.title }}</router-link>
          </li>
        </ul>
        <span v-else class="meta-text">暂无引用</span>
      </el-card>
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
.related { display: grid; gap: 12px; }
.practice-footer { border-top: 1px solid #dce5e2; margin-top: 20px; padding-top: 16px; }
.practice-footer a { color: #22675c; font-weight: 600; }
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
