<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getTopic, gradeCard, reviewCards, reviewCounts, startStarterBank, topicPracticeRoute } from '@/api/study'

const route = useRoute()
const topicId = computed(() => route.query.topic)
const mode = computed(() => route.query.mode === 'wrong' ? 'wrong' : topicId.value ? 'all' : 'due')
const topic = ref(null)
const cards = ref([])
const index = ref(0)
const revealed = ref(false)
const response = ref('')
const result = ref(null)
const objectiveTotal = ref(0)
const objectiveCorrect = ref(0)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const submitError = ref('')
const feedback = ref('')
const starterSize = ref(0)
const current = computed(() => cards.value[index.value])
let generation = 0

function resetAnswer() {
  response.value = ''
  result.value = null
  revealed.value = false
  submitError.value = ''
}

async function load() {
  const request = ++generation
  loading.value = true
  saving.value = false
  error.value = ''
  feedback.value = ''
  starterSize.value = 0
  index.value = 0
  objectiveTotal.value = 0
  objectiveCorrect.value = 0
  topic.value = null
  resetAnswer()
  try {
    const [queue, details] = await Promise.all([
      reviewCards(mode.value, topicId.value), topicId.value ? getTopic(topicId.value) : null,
    ])
    if (request !== generation) return
    topic.value = details
    let rows = queue
    if (!rows.length && mode.value === 'due') {
      const counts = await reviewCounts()
      if (request !== generation) return
      starterSize.value = counts.starter_size || 0
      if (starterSize.value && route.query.start === '1') {
        await startStarterBank()
        if (request !== generation) return
        rows = await reviewCards('due')
        if (request !== generation) return
        starterSize.value = 0
      }
    }
    cards.value = rows
  } catch (e) { if (request === generation) error.value = e.message }
  finally { if (request === generation) loading.value = false }
}
function advance() {
  index.value++
  resetAnswer()
}
async function grade(payload) {
  if (saving.value || result.value || !current.value) return
  const request = generation
  saving.value = true
  submitError.value = ''
  feedback.value = ''
  try {
    const graded = await gradeCard(current.value, payload)
    if (request !== generation) return
    feedback.value = graded.wrong ? '已加入错题本，下次复习日期为 ' + graded.due : '下次复习日期为 ' + graded.due
    if (current.value.kind === 'self') {
      advance()
    } else {
      result.value = graded
      objectiveTotal.value++
      if (graded.correct) objectiveCorrect.value++
    }
  } catch (e) { if (request === generation) submitError.value = e.message }
  finally { if (request === generation) saving.value = false }
}
async function start() {
  const request = generation
  loading.value = true
  try {
    await startStarterBank()
    if (request === generation) await load()
  } catch (e) {
    if (request === generation) { error.value = e.message; loading.value = false }
  }
}
watch(() => route.fullPath, load, { immediate: true })
</script>

<template>
  <section class="review">
    <router-link v-if="topicId" :to="'/topics/' + topicId">← 专题目录</router-link>
    <h1>{{ topicId ? (topic?.name || '专题') + ' · 专题练习' : '自测复习' }}</h1>
    <nav v-if="topicId" aria-label="专题练习范围">
      <router-link :to="topicPracticeRoute(topicId)" :class="{ active: mode === 'all' }">专题全部</router-link>
      <router-link :to="topicPracticeRoute(topicId, true)" :class="{ active: mode === 'wrong' }">只练错题</router-link>
    </nav>
    <nav v-else aria-label="复习范围">
      <router-link to="/review" :class="{ active: mode === 'due' }">今日自测</router-link>
      <router-link to="/review?mode=wrong" :class="{ active: mode === 'wrong' }">错题回顾</router-link>
    </nav>
    <el-skeleton v-if="loading" :rows="4" animated />
    <div v-else-if="error" role="alert">{{ error }} <el-button @click="load">刷新题目</el-button></div>
    <article v-else-if="current" :key="current.id" class="card">
      <small>第 {{ index + 1 }} / {{ cards.length }} 题 · {{ { choice: '单选题', number: '数值题', self: '简答自评' }[current.kind] }}</small>
      <h2 id="review-question">{{ current.question }}</h2>
      <template v-if="current.kind === 'self'">
        <el-button v-if="!revealed" type="primary" @click="revealed = true">显示答案</el-button>
        <template v-else>
          <div class="answer">{{ current.answer }}</div>
          <div class="actions"><el-button :disabled="saving" @click="grade({ remembered: false })">再练一次</el-button>
            <el-button type="primary" :disabled="saving" @click="grade({ remembered: true })">记住了</el-button></div>
        </template>
      </template>
      <form v-else @submit.prevent="grade({ response: response.trim() })">
        <fieldset v-if="current.kind === 'choice'" :disabled="saving || !!result" aria-labelledby="review-question">
          <label v-for="option in current.options" :key="option" class="option">
            <input type="radio" name="response" :value="option" v-model="response" />{{ option }}
          </label>
        </fieldset>
        <label v-else class="number">你的答案
          <input v-model="response" type="text" inputmode="decimal" maxlength="256" autocomplete="off" :disabled="saving || !!result" />
        </label>
        <el-button v-if="!result" type="primary" native-type="submit" :loading="saving" :disabled="!response.trim()">提交答案</el-button>
      </form>
      <div v-if="result" class="answer" :class="{ incorrect: !result.correct }" role="status">
        <strong>{{ result.correct ? '回答正确' : '回答错误' }}</strong>
        <p>正确答案为 {{ result.correct_answer }}</p>
        <p>{{ result.explanation }}</p>
      </div>
      <p v-if="current.kind === 'self' || result" class="source">
        <router-link :to="'/notes/' + current.note_id" target="_blank" rel="noopener">查看原笔记 · {{ current.title }} ↗</router-link>
      </p>
      <el-button v-if="result" type="primary" @click="advance">{{ index + 1 === cards.length ? '完成练习' : '下一题' }}</el-button>
      <p v-if="submitError" role="alert">{{ submitError }} <el-button size="small" @click="load">刷新题目</el-button></p>
    </article>
    <article v-else-if="starterSize" class="card">
      <h2>基础自测题库</h2>
      <p>{{ starterSize }} 道练习，涵盖算法、SQL、Python、HTTP 和检索评测。每题附参考答案和原笔记。</p>
      <el-button type="primary" @click="start">开始基础自测</el-button>
    </article>
    <article v-else class="card">
      <h2>{{ index ? '本轮已完成' : mode === 'wrong' ? '暂无错题' : topicId ? '本专题暂无练习题' : '今天没有待复习的题' }}</h2>
      <p v-if="index">完成 {{ index }} 题<span v-if="objectiveTotal">，客观题答对 {{ objectiveCorrect }} / {{ objectiveTotal }} 题</span>。</p>
      <p v-else-if="mode !== 'wrong'">在笔记详情中选中原文，点击「制作自测题」即可添加。</p>
      <router-link v-if="topicId && mode === 'wrong'" :to="topicPracticeRoute(topicId)">练习专题全部题目 →</router-link>
      <router-link v-else-if="topicId" :to="'/topics/' + topicId">返回专题目录 →</router-link>
      <router-link v-else to="/notes">打开全部笔记 →</router-link>
    </article>
    <p class="feedback" role="status">{{ feedback }}</p>
  </section>
</template>

<style scoped>
.review { max-width: 790px; margin: auto; }
nav { display: flex; gap: 20px; margin-bottom: 20px; }
nav a { padding: 6px 0; }
a { color: #22675c; text-decoration: none; }
.active { border-bottom: 2px solid; font-weight: bold; }
.card { background: white; border: 1px solid #dce5e2; border-radius: 12px; padding: clamp(18px, 4vw, 30px); }
h2 { white-space: pre-wrap; overflow-wrap: anywhere; }
small, .feedback { color: #617770; }
.answer { margin: 18px 0; padding: 18px; background: #edf4ee; border-radius: 6px; white-space: pre-wrap; overflow-wrap: anywhere; }
.incorrect { background: #fff2e7; }
.answer p { margin: 8px 0 0; }
.actions { margin-top: 20px; }
fieldset { border: 0; padding: 0; margin: 0 0 16px; display: grid; gap: 8px; }
.option { display: flex; gap: 10px; align-items: baseline; border: 1px solid #cfdbd5; border-radius: 6px; padding: 10px; cursor: pointer; overflow-wrap: anywhere; }
.option:has(:checked) { background: #edf4ee; border-color: #22675c; }
.number { display: grid; gap: 6px; max-width: 16em; margin-bottom: 16px; }
.number input { font: inherit; padding: 8px; border: 1px solid #929f98; border-radius: 6px; }
.source { font-size: 14px; }
</style>
