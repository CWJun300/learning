<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getTopic, orderTopic, readingLabels, readingRoute, removeFromTopic, topicPracticeRoute } from '@/api/study'
import TopicPicker from '@/components/TopicPicker.vue'

const props = defineProps({ id: { type: String, required: true } })
const topic = ref(null)
const error = ref('')
const picking = ref(false)
const busy = ref(false)
async function load() {
  try { topic.value = await getTopic(props.id); error.value = '' }
  catch (e) { error.value = e.message }
}
async function update(action) {
  if (busy.value) return
  busy.value = true
  try { await action() }
  catch (e) { ElMessage.error(e.message) }
  finally { await load(); busy.value = false }
}
function move(index, direction) {
  const ids = topic.value.items.map(i => i.note_id)
  const [id] = ids.splice(index, 1)
  ids.splice(index + direction, 0, id)
  update(() => orderTopic(props.id, ids))
}
onMounted(load)
</script>

<template>
  <section class="topic">
    <router-link to="/">← 学习首页</router-link>
    <el-alert v-if="error" type="error" :title="error" :closable="false" />
    <template v-else-if="topic">
      <header><div><h1>{{ topic.name }}</h1><p>已读 {{ topic.items.filter(i => i.status === 'read').length }} / {{ topic.items.length }} 篇</p></div>
        <el-button @click="picking = true">添加笔记</el-button></header>
      <nav v-if="topic.card_count" aria-label="专题练习">
        <router-link class="practice" :to="topicPracticeRoute(id)">练习本专题 · {{ topic.card_count }} 题</router-link>
        <router-link v-if="topic.wrong_count" :to="topicPracticeRoute(id, true)">只练错题 · {{ topic.wrong_count }} 题</router-link>
        <span v-else>暂无错题</span>
      </nav>
      <p v-else-if="topic.items.length">本专题还没有练习题，可在笔记正文中选取内容制作自测题。</p>
      <el-empty v-if="!topic.items.length" description="专题中没有可阅读的笔记" />
      <ol v-else>
        <li v-for="(item, index) in topic.items" :key="item.note_id">
          <div class="entry"><router-link :to="readingRoute(id, item.note_id)">{{ item.title }}</router-link>
            <small>{{ readingLabels[item.status] }}{{ topic.current_note_id === item.note_id ? ' · 上次读到' : '' }}</small></div>
          <div class="controls">
            <el-button size="small" :disabled="busy || index === 0" @click="move(index, -1)">上移</el-button>
            <el-button size="small" :disabled="busy || index === topic.items.length - 1" @click="move(index, 1)">下移</el-button>
            <el-button size="small" :disabled="busy" @click="update(() => removeFromTopic(id, item.note_id))">移出专题</el-button>
          </div>
        </li>
      </ol>
      <TopicPicker v-if="picking" :topic-id="topic.id" @close="picking = false" @saved="picking = false; load()" />
    </template>
  </section>
</template>

<style scoped>
.topic { max-width: 960px; margin: auto; }
header, li { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
header { margin: 18px 0; }
nav { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; font-size: 14px; }
nav span { color: #617770; }
nav .practice { background: #22675c; color: white; border-radius: 6px; padding: 8px 14px; }
h1 { margin: 0; color: #203938; }
p, small { color: #62756f; font-size: 13px; }
ol { list-style: none; padding: 0; background: white; border: 1px solid #dce5e2; border-radius: 8px; }
li { padding: 16px; }
li + li { border-top: 1px solid #eef1ef; }
.entry { display: grid; gap: 5px; }
a { color: #22675c; text-decoration: none; }
.controls { flex-shrink: 0; }
@media (max-width: 800px) { li { align-items: flex-start; flex-direction: column; } }
</style>
