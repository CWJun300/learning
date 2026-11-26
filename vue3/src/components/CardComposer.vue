<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createCard } from '@/api/study'

const props = defineProps({ noteId: Number, excerpt: String })
const emit = defineEmits(['close'])
const question = ref('')
const answer = ref(props.excerpt || '')
const busy = ref(false)
const error = ref('')
async function save() {
  if (busy.value) return
  busy.value = true
  try {
    await createCard({ note_id: props.noteId, question: question.value.trim(), answer: answer.value.trim() })
    ElMessage.success('已加入今日自测')
    emit('close')
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
</script>

<template>
  <el-dialog :model-value="true" title="制作自测题" width="min(560px, 94vw)" @close="emit('close')">
    <label>问题<el-input v-model="question" maxlength="500" placeholder="想用这段内容考自己什么？" /></label>
    <label>答案<el-input v-model="answer" type="textarea" :rows="5" placeholder="填写答案，或先在原文中选中一段文字" /></label>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <template #footer><el-button @click="emit('close')">取消</el-button>
      <el-button type="primary" :loading="busy" :disabled="!question.trim() || !answer.trim()" @click="save">保存自测题</el-button>
    </template>
  </el-dialog>
</template>
<style scoped>label { display: grid; gap: 6px; margin-bottom: 15px; }</style>
