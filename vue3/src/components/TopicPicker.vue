<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { suggestNotes } from '@/api/notes'
import { addToTopic, createTopic, listTopics } from '@/api/study'

const props = defineProps({
  initial: { type: Array, default: () => [] },
  topicId: { type: Number, default: null },
  chooseTopic: Boolean,
})
const emit = defineEmits(['close', 'saved'])
const selected = ref([...props.initial])
const topics = ref([])
const target = ref(props.topicId)
const name = ref('')
const query = ref('')
const choices = ref([])
const error = ref('')
const busy = ref(false)
let searchId = 0

async function lookup() {
  const id = ++searchId
  try {
    const result = await suggestNotes(query.value)
    if (id === searchId) choices.value = result
  } catch (e) { if (id === searchId) error.value = e.message }
}
function toggle(note) {
  const index = selected.value.findIndex(n => n.id === note.id)
  if (index < 0) selected.value.push(note)
  else selected.value.splice(index, 1)
}
async function save() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const ids = selected.value.map(n => n.id)
    let id = target.value
    if (id) await addToTopic(id, ids)
    else id = (await createTopic(name.value.trim(), ids)).id
    ElMessage.success('专题已保存')
    emit('saved', id)
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
onMounted(async () => {
  try {
    if (props.chooseTopic) topics.value = await listTopics()
  } catch (e) { error.value = e.message }
  await lookup()
})
</script>

<template>
  <el-dialog :model-value="true" :title="topicId ? '添加笔记' : chooseTopic ? '加入学习专题' : '新建专题'" width="min(540px, 94vw)"
    @close="emit('close')">
    <label v-if="chooseTopic && topics.length" class="field">专题
      <select v-model="target"><option :value="null">创建新专题</option>
        <option v-for="t in topics" :key="t.id" :value="t.id">{{ t.name }}</option>
      </select>
    </label>
    <label v-if="!target" class="field">专题名称
      <el-input v-model="name" maxlength="120" placeholder="例如：数据库期末复习" />
    </label>
    <label class="field">选择笔记
      <el-input v-model="query" clearable placeholder="按标题查找笔记" @input="lookup" />
    </label>
    <div class="choices">
      <label v-for="n in choices" :key="n.id"><input type="checkbox"
        :checked="selected.some(s => s.id === n.id)" @change="toggle(n)" /> {{ n.title }}</label>
      <p v-if="!choices.length">没有匹配的笔记</p>
    </div>
    <div class="picked"><el-tag v-for="n in selected" :key="n.id" closable @close="toggle(n)">{{ n.title }}</el-tag></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <template #footer>
      <el-button @click="emit('close')">取消</el-button>
      <el-button type="primary" :disabled="(!target && !name.trim()) || !selected.length"
        :loading="busy" @click="save">保存专题（{{ selected.length }}）</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.field { display: grid; gap: 6px; margin-bottom: 14px; font-weight: 600; }
select { padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px; color: #303133; }
.choices { max-height: 170px; overflow: auto; }
.choices label { display: block; padding: 5px 0; cursor: pointer; }
.picked { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px; }
</style>
