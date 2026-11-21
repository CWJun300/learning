<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getStats, listNotes, listTags } from '@/api/notes'

const router = useRouter()

const notes = ref([])
const total = ref(0)
const page = ref(1)
const size = 10
const activeTag = ref('')
const tags = ref([])
const stats = ref(null)
const loading = ref(false)

async function loadNotes() {
  loading.value = true
  try {
    const params = { page: page.value, size }
    if (activeTag.value) params.tag = activeTag.value
    const data = await listNotes(params)
    notes.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function loadSidebar() {
  try {
    const [tagList, statData] = await Promise.all([listTags(), getStats()])
    tags.value = tagList
    stats.value = statData
  } catch {
    // 侧边栏失败不影响主列表
  }
}

function selectTag(name) {
  activeTag.value = activeTag.value === name ? '' : name
  page.value = 1
  loadNotes()
}

function changePage(next) {
  page.value = next
  loadNotes()
}

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function openNote(id) {
  router.push(`/notes/${id}`)
}

onMounted(() => {
  loadNotes()
  loadSidebar()
})
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <el-card shadow="never" class="stat-card">
        <div class="stat-row">
          <span class="stat-num">{{ stats?.note_count ?? '-' }}</span>
          <span class="stat-label">篇笔记</span>
        </div>
        <div class="stat-row">
          <span class="stat-num">{{ stats?.term_count ?? '-' }}</span>
          <span class="stat-label">个词条</span>
        </div>
        <div class="stat-row">
          <span class="stat-num">{{ stats?.avg_note_length ?? '-' }}</span>
          <span class="stat-label">平均词数</span>
        </div>
      </el-card>

      <el-card shadow="never" class="tag-card">
        <template #header>
          <div class="card-header">
            <span>标签</span>
            <el-button v-if="activeTag" link type="primary" @click="selectTag(activeTag)">
              清除
            </el-button>
          </div>
        </template>
        <el-empty v-if="!tags.length" description="暂无标签" :image-size="60" />
        <div v-else class="tag-list">
          <el-tag
            v-for="tag in tags"
            :key="tag.name"
            :type="activeTag === tag.name ? 'primary' : 'info'"
            :effect="activeTag === tag.name ? 'dark' : 'plain'"
            class="tag-item"
            @click="selectTag(tag.name)"
          >
            {{ tag.name }} · {{ tag.count }}
          </el-tag>
        </div>
      </el-card>
    </aside>

    <section class="content">
      <div class="toolbar">
        <h2 class="title">
          全部笔记
          <span v-if="activeTag" class="title-tag">#{{ activeTag }}</span>
        </h2>
        <el-button type="primary" @click="router.push('/notes/new')">新建笔记</el-button>
      </div>

      <el-skeleton v-if="loading" :rows="4" animated />

      <template v-else>
        <el-empty v-if="!notes.length" description="还没有笔记，去写第一篇吧" />

        <div v-else class="note-grid">
          <el-card
            v-for="note in notes"
            :key="note.id"
            class="note-card"
            shadow="hover"
            @click="openNote(note.id)"
          >
            <div class="note-title">{{ note.title }}</div>
            <div class="note-excerpt">
              {{ (note.content || '（无正文）').slice(0, 120) }}
            </div>
            <div class="note-footer">
              <div class="note-tags">
                <el-tag v-for="tag in note.tags" :key="tag.id" size="small" type="info">
                  {{ tag.name }}
                </el-tag>
              </div>
              <span class="note-date">{{ formatDate(note.updated_at) }}</span>
            </div>
          </el-card>
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
      </template>
    </section>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.sidebar {
  width: 220px;
  flex: 0 0 220px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.content {
  flex: 1;
  min-width: 0;
}
.stat-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.stat-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.stat-num {
  font-size: 20px;
  font-weight: 600;
  color: #409eff;
}
.stat-label {
  font-size: 12px;
  color: #909399;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tag-item {
  cursor: pointer;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.title {
  margin: 0;
  font-size: 18px;
}
.title-tag {
  color: #409eff;
  font-size: 14px;
  margin-left: 6px;
}
.note-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.note-card {
  cursor: pointer;
}
.note-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.note-excerpt {
  font-size: 13px;
  color: #606266;
  min-height: 40px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.note-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  gap: 8px;
}
.note-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.note-date {
  font-size: 11px;
  color: #c0c4cc;
  white-space: nowrap;
}
.pager {
  margin-top: 16px;
  justify-content: center;
}
</style>
