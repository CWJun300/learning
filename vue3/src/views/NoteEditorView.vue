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

const pickerOpen = ref(false)
const newTag = ref('')

const isEdit = computed(() => Boolean(props.id))

async function loadTags() {
  try {
    knownTags.value = (await listTags()).map((tag) => tag.name)
  } catch {
    // 标签补全失败不影响编辑
  }
}

/** 选中一个标签：加到列表里，并关闭面板（要再加就再点按钮） */
function addTag(name) {
  const value = (name || '').trim()
  if (value && !form.tags.includes(value)) {
    form.tags.push(value)
  }
  pickerOpen.value = false
}

/** 面板底部新建标签 */
function addNewTag() {
  const value = newTag.value.trim()
  if (!value) {
    pickerOpen.value = false
    return
  }
  addTag(value)
  newTag.value = ''
}

function removeTag(name) {
  const index = form.tags.indexOf(name)
  if (index >= 0) form.tags.splice(index, 1)
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

    <!-- 标签：按钮触发，面板里点选；标签块显示在面板外 -->
    <div class="tag-block">
      <div class="tag-line">
        <span class="tag-label">标签</span>

        <el-popover
          v-model:visible="pickerOpen"
          placement="bottom-start"
          :width="260"
          trigger="click"
          popper-class="tag-picker-popper"
        >
          <template #reference>
            <el-button class="tag-picker-btn">请选择标签</el-button>
          </template>

          <div class="picker">
            <div class="picker-list">
              <div
                v-for="name in knownTags"
                :key="name"
                class="picker-item"
                :class="{ picked: form.tags.includes(name) }"
                @click="addTag(name)"
              >
                {{ name }}
                <span v-if="form.tags.includes(name)" class="picker-check">已选</span>
              </div>
              <div v-if="!knownTags.length" class="picker-empty">暂无标签，可在下方新建</div>
            </div>

            <div class="picker-new">
              <el-input
                v-model="newTag"
                size="small"
                placeholder="新建标签"
                @keyup.enter="addNewTag"
              />
              <el-button size="small" type="primary" @click="addNewTag">添加</el-button>
            </div>
          </div>
        </el-popover>
      </div>

      <div v-if="form.tags.length" class="tag-chips">
        <el-tag
          v-for="name in form.tags"
          :key="name"
          closable
          @close="removeTag(name)"
        >
          {{ name }}
        </el-tag>
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
  gap: 10px;
}
.tag-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}
.tag-picker-btn {
  min-width: 140px;
  justify-content: space-between;
}
.tag-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-height: 24px;
  padding-left: 42px;
}

/* ---------- 弹出面板 ---------- */
.picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.picker-list {
  max-height: 220px;
  overflow-y: auto;
}
.picker-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
}
.picker-item:hover {
  background: #f5f7fa;
  color: #409eff;
}
.picker-item.picked {
  color: #409eff;
  font-weight: 600;
}
.picker-check {
  font-size: 11px;
  color: #a8abb2;
  font-weight: 400;
}
.picker-empty {
  font-size: 12px;
  color: #c0c4cc;
  padding: 6px 8px;
}
.picker-new {
  display: flex;
  gap: 6px;
  border-top: 1px solid #f0f2f5;
  padding-top: 8px;
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
