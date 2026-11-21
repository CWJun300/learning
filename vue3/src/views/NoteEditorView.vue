<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

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

const NEW_TAG = '__new_tag__'

const isEdit = computed(() => Boolean(props.id))

async function loadTags() {
  try {
    knownTags.value = (await listTags()).map((tag) => tag.name)
  } catch {
    // 标签补全失败不影响编辑
  }
}

/** 选中一个标签：加到列表里（下拉菜单点完会自动关闭） */
function addTag(name) {
  const value = (name || '').trim()
  if (value && !form.tags.includes(value)) {
    form.tags.push(value)
  }
}

/** 下拉菜单命令分发 */
async function onCommand(command) {
  if (command === NEW_TAG) {
    try {
      const { value } = await ElMessageBox.prompt('输入新标签名称', '新建标签', {
        confirmButtonText: '添加',
        cancelButtonText: '取消',
        inputPlaceholder: '例如：检索、MySQL',
        inputValidator: (text) => (text && text.trim() ? true : '标签不能为空'),
      })
      addTag(value)
      // 让新标签下次也能出现在菜单里
      if (value && !knownTags.value.includes(value.trim())) {
        knownTags.value.push(value.trim())
      }
    } catch {
      // 用户取消
    }
    return
  }
  addTag(command)
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

    <!-- 标签：下拉菜单选一个就关闭；已选标签显示在菜单外 -->
    <div class="tag-block">
      <div class="tag-line">
        <span class="tag-label">标签</span>

        <el-dropdown trigger="click" @command="onCommand">
          <el-button class="tag-picker-btn">请选择标签</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="name in knownTags" :key="name" :command="name">
                {{ name }}
              </el-dropdown-item>
              <el-dropdown-item v-if="!knownTags.length" disabled>暂无标签</el-dropdown-item>
              <el-dropdown-item :command="NEW_TAG" divided>＋ 新建标签</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
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
