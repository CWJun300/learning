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
const newTag = ref('')
const loading = ref(false)
const saving = ref(false)

const isEdit = computed(() => Boolean(props.id))

async function loadTags() {
  try {
    const list = await listTags()
    knownTags.value = list.map((tag) => tag.name)
  } catch (error) {
    ElMessage.error(`标签加载失败：${error.message}`)
  }
}

function addTag(name) {
  const value = (name || '').trim()
  if (!value) return
  if (form.value.tags.includes(value)) {
    ElMessage.info(`「${value}」已经选过了`)
    return
  }
  form.value.tags.push(value)
  // 便于排查：选中后可在控制台看到当前标签数组
  console.debug('[tag] added:', value, '->', [...form.value.tags])
}

/** 原生 select：选完浏览器自动收起，然后把 value 复位回占位项 */
function onPick(event) {
  const value = event.target.value
  if (value) addTag(value)
  event.target.value = ''
}

/** 手动输入新标签 */
function addNewTag() {
  const value = newTag.value.trim()
  if (!value) return
  addTag(value)
  if (!knownTags.value.includes(value)) knownTags.value.push(value)
  newTag.value = ''
}

function removeTag(name) {
  const index = form.value.tags.indexOf(name)
  if (index >= 0) form.value.tags.splice(index, 1)
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
    if (isEdit.value) {
      const note = await updateNote(props.id, form.value)
      ElMessage.success('已保存')
      router.push(`/notes/${note.id}`)
    } else {
      await createNote(form.value)
      ElMessage.success('已创建')
      router.push('/')
    }
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

    <!-- 标签：原生 select 选一个自动收起，标签显示在下面一行 -->
    <div class="tag-block">
      <div class="tag-line">
        <span class="tag-label">标签</span>

        <select class="tag-native" @change="onPick">
          <option value="" selected>请选择标签</option>
          <option v-for="name in knownTags" :key="name" :value="name">{{ name }}</option>
        </select>

        <span class="tag-divider">|</span>

        <input
          v-model="newTag"
          class="tag-input-new"
          placeholder="新建标签"
          @keyup.enter="addNewTag"
        />
        <el-button size="small" @click="addNewTag">添加</el-button>

        <span class="tag-count">已选 {{ form.tags.length }} 个</span>
      </div>

      <div class="tag-chips">
        <el-tag
          v-for="name in form.tags"
          :key="name"
          closable
          @close="removeTag(name)"
        >
          {{ name }}
        </el-tag>
        <span v-if="!form.tags.length" class="tag-empty">还没有选择标签</span>
      </div>
    </div>

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
  gap: 14px;
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

/* ---------- 标签区 ---------- */
.tag-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}
.tag-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.tag-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}
.tag-native {
  height: 32px;
  min-width: 160px;
  padding: 0 10px;
  font-size: 13px;
  color: #303133;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  outline: none;
  cursor: pointer;
}
.tag-native:focus {
  border-color: #409eff;
}
.tag-divider {
  color: #dcdfe6;
}
.tag-input-new {
  height: 32px;
  width: 140px;
  padding: 0 10px;
  font-size: 13px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  outline: none;
}
.tag-input-new:focus {
  border-color: #409eff;
}
.tag-count {
  font-size: 12px;
  color: #a8abb2;
}
.tag-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-height: 24px;
  padding-left: 42px;
}
.tag-empty {
  font-size: 12px;
  color: #c0c4cc;
}

/* ---------- 编辑与预览 ---------- */
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
