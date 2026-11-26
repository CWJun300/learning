<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTopic, readingLabels, readingRoute, setReading } from '@/api/study'

const props = defineProps({ topicId: String, noteId: Number })
const emit = defineEmits(['ready'])
const router = useRouter()
const topic = ref(null)
const busy = ref(false)
const index = computed(() => topic.value?.items.findIndex(i => i.note_id === props.noteId) ?? -1)
const current = computed(() => topic.value?.items[index.value])
const next = computed(() => topic.value?.items[index.value + 1])
onMounted(async () => {
  try {
    topic.value = await getTopic(props.topicId)
    if (current.value) {
      emit('ready', topic.value)
      await setReading(props.topicId, props.noteId)
    }
  } catch (e) { ElMessage.error(e.message) }
})
async function mark(status, advance = false) {
  if (busy.value) return
  busy.value = true
  try {
    await setReading(props.topicId, props.noteId, status)
    current.value.status = status
    if (advance) {
      router.push(next.value ? readingRoute(props.topicId, next.value.note_id) : '/topics/' + props.topicId)
    }
  } catch (e) { ElMessage.error(e.message) }
  finally { busy.value = false }
}
</script>

<template>
  <div v-if="current" class="reading">
    <router-link :to="'/topics/' + topicId">← {{ topic.name }}</router-link>
    <span>第 {{ index + 1 }} / {{ topic.items.length }} 篇</span>
    <select aria-label="阅读状态" :value="current.status" :disabled="busy" @change="mark($event.target.value)">
      <option v-for="(label, value) in readingLabels" :value="value" :key="value">{{ label }}</option>
    </select>
    <el-button size="small" :loading="busy" @click="mark('read', true)">{{ next ? '标记已读并读下一篇' : '标记已读并返回专题' }}</el-button>
  </div>
</template>
<style scoped>
.reading { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; background: #e8f2ec; padding: 12px; margin-bottom: 16px; border-radius: 6px; font-size: 13px; }
.reading a { color: #205d50; margin-right: auto; }
select { padding: 4px; }
</style>
