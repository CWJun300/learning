<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { importNotes } from '@/api/notes'

const router = useRouter()

const files = ref([])
const dragging = ref(false)
const submitting = ref(false)
const result = ref(null)

const ACCEPT = ['.md', '.markdown', '.txt', '.json']

function isSupported(name) {
  const lower = (name || '').toLowerCase()
  return ACCEPT.some((ext) => lower.endsWith(ext))
}

async function readFiles(fileList) {
  const incoming = []
  for (const file of Array.from(fileList || [])) {
    if (!isSupported(file.name)) {
      ElMessage.warning(`跳过不支持的文件：${file.name}`)
      continue
    }
    try {
      const content = await file.text()
      incoming.push({ name: file.name, content, size: file.size })
    } catch {
      ElMessage.error(`${file.name} 读取失败`)
    }
  }

  const existing = new Set(files.value.map((item) => item.name))
  files.value.push(...incoming.filter((item) => !existing.has(item.name)))
  result.value = null
}

function onPick(event) {
  readFiles(event.target.files)
  event.target.value = ''
}

function onDrop(event) {
  dragging.value = false
  readFiles(event.dataTransfer?.files)
}

function removeFile(name) {
  files.value = files.value.filter((item) => item.name !== name)
}

function clearAll() {
  files.value = []
  result.value = null
}

async function submit() {
  if (!files.value.length) {
    ElMessage.warning('请先选择要导入的文件')
    return
  }
  submitting.value = true
  try {
    result.value = await importNotes(
      files.value.map((item) => ({ name: item.name, content: item.content })),
    )
    if (result.value.imported > 0) {
      ElMessage.success(`成功导入 ${result.value.imported} 篇笔记`)
      files.value = []
    } else {
      ElMessage.info('没有新增笔记')
    }
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    submitting.value = false
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div class="import-page">
    <h2 class="title">批量导入笔记</h2>

    <div
      class="drop-zone"
      :class="{ dragging }"
      @click="$refs.picker.click()"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <div class="drop-main">把文件拖到这里，或点击选择</div>
      <div class="drop-sub">支持 .md / .txt / .json，可一次选多个</div>
      <input
        ref="picker"
        type="file"
        multiple
        accept=".md,.markdown,.txt,.json"
        class="hidden-input"
        @change="onPick"
      />
    </div>

    <div v-if="files.length" class="file-panel">
      <div class="file-head">
        <span>已选 {{ files.length }} 个文件</span>
        <el-button link type="danger" @click="clearAll">清空</el-button>
      </div>
      <div v-for="item in files" :key="item.name" class="file-row">
        <span class="file-name" :title="item.name">{{ item.name }}</span>
        <span class="file-size">{{ formatSize(item.size) }}</span>
        <el-button link type="danger" @click="removeFile(item.name)">移除</el-button>
      </div>
      <el-button type="primary" :loading="submitting" class="submit-btn" @click="submit">
        开始导入
      </el-button>
    </div>

    <div v-if="result" class="result-panel">
      <div class="result-line">
        导入成功 <b>{{ result.imported }}</b> 篇，跳过重复 <b>{{ result.skipped }}</b> 篇
      </div>

      <div v-if="result.titles.length" class="title-list">
        <el-tag v-for="name in result.titles" :key="name" size="small" type="success">
          {{ name }}
        </el-tag>
      </div>

      <div v-if="result.failed.length" class="fail-list">
        <div class="fail-title">失败 {{ result.failed.length }} 个：</div>
        <div v-for="item in result.failed" :key="item.name" class="fail-row">
          <span class="fail-name">{{ item.name }}</span>
          <span class="fail-reason">{{ item.reason }}</span>
        </div>
      </div>

      <el-button v-if="result.imported > 0" type="primary" plain @click="router.push('/')">
        去看看导入的笔记
      </el-button>
    </div>

    <el-card shadow="never" class="help-card">
      <template #header>格式说明</template>
      <div class="help-item">
        <b>.md / .txt</b>：第一个 <code># 标题</code> 作为笔记标题，没有就用文件名；正文全部保留。
      </div>
      <div class="help-item">
        <b>可选 front matter</b>（写在文件开头）：
        <pre>---
title: 自定义标题
tags: Vue, 前端
---</pre>
      </div>
      <div class="help-item">
        <b>.json</b>：数组，或 <code>{"notes": [...]}</code>，每项
        <code>{"title": "...", "content": "...", "tags": ["..."]}</code>
      </div>
      <div class="help-item muted">
        标题重复的笔记会自动跳过；单文件上限 1MB，一次最多 50 个文件。
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.import-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 900px;
}
.title {
  margin: 0;
  font-size: 18px;
}
.drop-zone {
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  padding: 34px 20px;
  text-align: center;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
}
.drop-zone:hover,
.drop-zone.dragging {
  border-color: #409eff;
  background: #ecf5ff;
}
.drop-main {
  font-size: 15px;
  color: #303133;
}
.drop-sub {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}
.hidden-input {
  display: none;
}
.file-panel {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px 16px;
}
.file-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}
.file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px dashed #f0f2f5;
  font-size: 13px;
}
.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-size {
  color: #a8abb2;
  font-size: 12px;
}
.submit-btn {
  margin-top: 12px;
}
.result-panel {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 6px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.result-line {
  font-size: 13px;
  color: #529b2e;
}
.title-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.fail-list {
  font-size: 12px;
  color: #f56c6c;
}
.fail-title {
  margin-bottom: 4px;
}
.fail-row {
  display: flex;
  gap: 8px;
}
.fail-name {
  font-weight: 600;
}
.help-card {
  background: #fafafa;
}
.help-item {
  font-size: 13px;
  color: #606266;
  line-height: 1.9;
}
.help-item pre {
  margin: 6px 0 0;
  background: #f5f7fa;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 12px;
  white-space: pre-wrap;
}
.help-item code {
  background: #f5f7fa;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
}
.muted {
  color: #909399;
  font-size: 12px;
}
</style>
