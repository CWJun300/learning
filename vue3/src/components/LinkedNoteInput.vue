<script setup>
import { nextTick, ref } from 'vue'
import { suggestNotes } from '@/api/notes'

const content = defineModel({ type: String, default: '' })
const editor = ref(null)
const matches = ref([])
const query = ref(null)
const status = ref('')
const selected = ref(0)
let revision = 0

function close() {
  revision++
  query.value = null
  matches.value = []
  status.value = ''
}

function fragment() {
  const field = editor.value
  if (field.selectionStart !== field.selectionEnd) return null
  return field.value.slice(0, field.selectionStart).match(/\[\[([^[\]\n]*)$/)
}

async function suggest() {
  const match = fragment()
  if (!match) return close()
  if (query.value === match[1]) return
  const request = ++revision
  query.value = match[1]
  selected.value = 0
  matches.value = []
  status.value = '正在查找…'
  try {
    const rows = await suggestNotes(match[1])
    if (request === revision) {
      matches.value = rows
      status.value = rows.length ? '' : '没有匹配的笔记'
    }
  } catch (error) {
    if (request === revision) status.value = error.message
  }
}

async function insert(note) {
  const match = fragment()
  if (!match || !note) return
  const field = editor.value
  const start = field.selectionStart - match[0].length
  const end = field.selectionEnd + (field.value.startsWith(']]', field.selectionEnd) ? 2 : 0)
  const title = note.title.replace(/\s+/g, ' ').replace(/[\\[\]*_~<>!&\x60]/g, '\\$&')
  const link = '[' + title + '](/notes/' + note.id + ')'
  content.value = field.value.slice(0, start) + link + field.value.slice(end)
  close()
  await nextTick()
  field.focus()
  field.setSelectionRange(start + link.length, start + link.length)
}

function keydown(event) {
  if (event.isComposing || query.value === null) return
  if (event.key === 'Escape') return close()
  if (!matches.value.length) return
  if (event.key === 'Enter') {
    event.preventDefault()
    insert(matches.value[selected.value])
  } else if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
    event.preventDefault()
    const count = matches.value.length
    selected.value = (selected.value + (event.key === 'ArrowDown' ? 1 : -1) + count) % count
  }
}
</script>

<template>
  <div class="link-input">
  <textarea ref="editor" v-model="content" rows="22" aria-label="Markdown 正文"
    placeholder="输入 Markdown，输入 [[ 搜索并引用笔记"
    @input="suggest" @click="suggest" @blur="close" @keydown="keydown"
    @keyup.left="suggest" @keyup.right="suggest" />
  <div v-if="query !== null" class="suggestions" aria-label="可引用的笔记">
    <small v-if="status" role="status">{{ status }}</small>
    <button v-for="(note, index) in matches" :key="note.id" type="button"
      :class="{ selected: index === selected }" @mousedown.prevent @click="insert(note)">
      {{ note.title }} <small>#{{ note.id }}</small>
    </button>
  </div>
  </div>
</template>

<style scoped>
.link-input { display: flex; flex-direction: column; }
textarea { box-sizing: border-box; width: 100%; padding: 10px 12px; border: 1px solid #dcdfe6; border-radius: 4px; color: #303133; font: inherit; line-height: 1.6; resize: vertical; }
textarea:focus-visible { outline: 2px solid #409eff; outline-offset: -1px; }
.suggestions { order: -1; border: 1px solid #dcdfe6; background: white; padding: 6px; max-height: 150px; overflow: auto; border-radius: 4px; }
button { display: block; width: 100%; padding: 5px 8px; border: 0; background: white; text-align: left; cursor: pointer; }
button.selected, button:hover { background: #ecf5ff; }
small { color: #606266; }
</style>
