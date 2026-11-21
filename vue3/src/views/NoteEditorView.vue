<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { createNote, getNote, listTags, updateNote } from '@/api/notes'
import MarkdownView from '@/components/MarkdownView.vue'

const props = defineProps({
  id: { type: String, default: '' },
})

const router = useRouter()
const form = ref({ title: '', content: '', tags: [] })
const knownTags = ref([])
const loading = ref(false)
const saving = ref(false)

const isEdit = computed(() => Boolean(props.id))

async function loadTags() {
  try {
    knownTags.value = (await listTags()).map((tag) => tag.name)
  } catch {
    // 标签补全失败不影响编辑
  }
}

async function load() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const note = await getNote(props.id)
    form.value = {
      title: note.title,
      content: note.content,
      tags: note.tags.map((tag) => tag.name),
    }
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!form.value.title.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }
  saving.value = true
  try {
    const note = isEdit.value
      ? await updateNote(props.id, form.value)
      : await createNote(form.value)
    ElMessage.success(isEdit.value ? '已保存' : '已创建')
    router.push(`/notes/${note.id}`)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

/** Ctrl+S / Cmd+S 保存 */
function onKeydown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    save()
  }
}

onMounted(() => {
  load()
  loadTags()
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <el-skeleton v-if="loading" :rows="6" animated />

  <div v-else class="editor">
    <div class="editor-head">
      <el-input
        v-model="form.title"
        placeholder="笔记标题"
        size="large"
        maxlength="200"
        show-word-limit
      />
      <div class="editor-actions">
        <span class="hint">Ctrl + S 保存</span>
        <el-button @click="router.back()">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
    </div>

    <el-select
      v-model="form.tags"
      class="tag-select"
      multiple
      filterable
      allow-create
      default-first-option
      :reserve-keyword="false"
      placeholder="输入标签后回车，例如：检索、MySQL（可直接新建）"
    >
      <el-option v-for="name in knownTags" :key="name" :label="name" :value="name" />
    </el-select>

    <div class="editor-body">
      <div class="pane">
        <div class="pane-title">Markdown</div>
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="22"
          resize="none"
          placeholder="支持 Markdown 语法，右侧实时预览"
        />
      </div>
      <div class="pane">
        <div class="pane-title">预览</div>
        <div class="preview">
          <MarkdownView :source="form.content" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.editor-head {
  display: flex;
  gap: 12px;
  align-items: center;
}
.editor-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.hint {
  font-size: 12px;
  color: #c0c4cc;
}
.tag-select {
  width: 520px;
  max-width: 100%;
}
.editor-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.pane {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.pane-title {
  font-size: 12px;
  color: #909399;
}
.preview {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 12px 16px;
  height: 100%;
  overflow: auto;
  background: #fff;
}
</style>
