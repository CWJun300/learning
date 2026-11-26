<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listNotes } from '@/api/notes'
import { listTopics, readingRoute, reviewCounts } from '@/api/study'
import TopicPicker from '@/components/TopicPicker.vue'

const router = useRouter()
const topics = ref([])
const counts = ref({ due: 0, wrong: 0 })
const recent = ref([])
const picking = ref(false)
const loading = ref(true)
const error = ref('')
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [all, stats, notes] = await Promise.all([listTopics(), reviewCounts(), listNotes({ size: 4 })])
    topics.value = all
    counts.value = stats
    recent.value = notes.items
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
function resume(t) {
  const id = t.current_note_id || t.items.find(i => i.status !== 'read')?.note_id || t.items[0]?.note_id
  return id ? readingRoute(t.id, id) : '/topics/' + t.id
}
function readCount(t) { return t.items.filter(i => i.status === 'read').length }
onMounted(load)
</script>

<template>
  <main class="study">
    <h1>学习首页</h1>
    <el-skeleton v-if="loading" :rows="4" animated />
    <el-result v-else-if="error" icon="warning" :title="error"><template #extra><el-button @click="load">重试</el-button></template></el-result>
    <template v-else>
      <div class="overview">
        <section class="panel continue">
          <h2>继续学习</h2>
          <template v-if="topics.length">
            <h3>{{ topics[0].name }}</h3>
            <p>已读 {{ readCount(topics[0]) }} / {{ topics[0].items.length }} 篇</p>
            <router-link class="action" :to="resume(topics[0])">继续阅读 →</router-link>
          </template>
          <template v-else>
            <h3>创建第一个学习专题</h3>
            <p>从笔记中选几篇，按自己的顺序阅读。</p>
            <button class="action" @click="picking = true">新建专题</button>
          </template>
        </section>
        <section class="panel today">
          <h2>今日自测</h2>
          <div class="number">{{ counts.due || counts.starter_size || 0 }} <small>{{ counts.starter_size ? '道基础题' : '题待复习' }}</small></div>
          <p><router-link to="/review?mode=wrong">错题回顾 · {{ counts.wrong }} 题</router-link></p>
          <router-link v-if="counts.starter_size" to="/review?start=1">开始基础自测 →</router-link>
          <router-link v-else :to="counts.due ? '/review' : '/notes'">{{ counts.due ? '开始自测 →' : '从笔记制作自测题 →' }}</router-link>
        </section>
      </div>
      <section>
        <div class="section-head"><h2>我的专题</h2><el-button v-if="topics.length" @click="picking = true">新建专题</el-button></div>
        <div v-if="topics.length" class="rows">
          <router-link v-for="t in topics" :key="t.id" class="row" :to="'/topics/' + t.id">
            <strong>{{ t.name }}</strong><span>已读 {{ readCount(t) }} / {{ t.items.length }} 篇　›</span>
          </router-link>
        </div>
        <p v-else class="muted">还没有专题，也可以在搜索结果中勾选笔记创建。</p>
      </section>
      <section>
        <div class="section-head"><h2>最近更新的笔记</h2><router-link to="/notes">全部笔记 →</router-link></div>
        <div v-if="recent.length" class="rows">
          <router-link v-for="n in recent" :key="n.id" class="row" :to="'/notes/' + n.id">
            <strong>{{ n.title }}</strong><span>{{ n.updated_at.slice(0, 10) }}</span>
          </router-link>
        </div>
        <router-link v-else to="/notes/new">写第一篇笔记</router-link>
      </section>
    </template>
    <TopicPicker v-if="picking" @close="picking = false" @saved="id => router.push('/topics/' + id)" />
  </main>
</template>

<style scoped>
.study { max-width: 1080px; margin: 0 auto; color: #203938; }
h1 { font-size: 28px; margin: 4px 0 24px; }
h2 { font-size: 19px; margin: 0; }
.section-head { display: flex; justify-content: space-between; align-items: center; margin: 28px 0 12px; }
.overview { display: grid; grid-template-columns: 1.45fr 1fr; gap: 16px; }
.panel { border-radius: 12px; padding: 24px 28px; }
.panel h2 { font-size: 15px; }
.continue { background: #174e49; color: white; }
.today { background: #e8f0e7; }
.panel h3, .number { font-size: 27px; margin: 15px 0 4px; }
.panel p { margin: 6px 0 18px; font-size: 14px; }
.continue p { color: #dfefea; }
.number { font-weight: 700; }
.number small { font-size: 13px; font-weight: 400; }
.action { display: inline-block; background: white; color: #174e49; border: none; padding: 7px 14px; border-radius: 5px; font: inherit; cursor: pointer; }
a { text-decoration: none; color: #22675c; }
.rows { background: white; border: 1px solid #dce5e2; border-radius: 8px; overflow: hidden; }
.row { display: flex; gap: 12px; align-items: center; justify-content: space-between; padding: 15px 18px; color: inherit; }
.row + .row { border-top: 1px solid #eef1ef; }
.row:hover { background: #f3f8f6; }
.row span, .muted { font-size: 13px; color: #637570; }
@media (max-width: 850px) { .overview { grid-template-columns: 1fr; } }
</style>
