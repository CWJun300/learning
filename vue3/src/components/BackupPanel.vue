<script setup>
import { inject, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { restoreBackup } from '@/api/notes'

const busy = ref(false)
const result = ref('')
const failed = ref(false)
const refreshHealth = inject('refreshHealth')

async function restore(event) {
  const file = event.target.files[0]
  event.target.value = ''
  if (!file) return
  busy.value = true
  result.value = ''
  failed.value = false
  try {
    const raw = await file.text()
    const backup = JSON.parse(raw)
    if (backup?.format !== 'personal-kb' || ![1, 2].includes(backup.version) || !Array.isArray(backup.notes)) {
      throw new Error('请选择从本知识库导出的 JSON 备份')
    }
    try {
      await ElMessageBox.confirm(
        '共 ' + backup.notes.length + ' 篇（含回收站）。相同记录会跳过，遇到 ID 冲突会取消整次恢复。',
        '恢复 ' + file.name, { confirmButtonText: '恢复备份', cancelButtonText: '取消' })
    } catch { return }
    const summary = await restoreBackup(raw)
    await refreshHealth()
    result.value = '已恢复 ' + summary.restored + ' 篇，跳过相同记录 ' + summary.skipped + ' 篇。'
    if (backup.study) result.value += ' 已同步专题与自测进度。'
  } catch (error) {
    failed.value = true
    result.value = error instanceof SyntaxError ? '文件不是有效的 JSON' : error.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>整库备份</template>
    <p>备份包含笔记、回收站、专题阅读进度和自测记录。</p>
    <a class="el-button" href="/api/backup" download="knowledge-base.json">下载 JSON 备份</a>
    <el-button :loading="busy" @click="$refs.picker.click()">恢复备份</el-button>
    <input ref="picker" type="file" accept=".json" hidden @change="restore" />
    <p v-if="result" role="status" :class="{ error: failed }">{{ result }}</p>
  </el-card>
</template>

<style scoped>
p { margin: 0 0 12px; font-size: 14px; color: #606266; }
p[role] { margin: 12px 0 0; }
p.error { color: #b32d29; }
a { text-decoration: none; }
</style>
