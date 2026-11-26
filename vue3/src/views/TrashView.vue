<script setup>
import { inject, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listTrash, restoreNote } from '@/api/notes'

const items = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const restoring = ref(null)
const errorText = ref('')
const refreshHealth = inject('refreshHealth')

async function load(next = 1) {
  loading.value = true
  errorText.value = ''
  try {
    let result = await listTrash(next)
    if (next > 1 && !result.items.length) {
      next = Math.max(1, Math.ceil(result.total / result.size))
      result = await listTrash(next)
    }
    page.value = next
    items.value = result.items
    total.value = result.total
  } catch (error) {
    errorText.value = error.message
  } finally {
    loading.value = false
  }
}
async function restore(item) {
  restoring.value = item.id
  try {
    await restoreNote(item.id)
    ElMessage.success('已恢复《' + item.title + '》')
    await load(page.value)
    await refreshHealth()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    restoring.value = null
  }
}
onMounted(() => load())
</script>

<template>
  <section>
    <h2>回收站</h2>
    <el-alert v-if="errorText" :title="errorText" type="error" :closable="false" />
    <el-skeleton v-else-if="loading" :rows="4" animated />
    <el-empty v-else-if="!items.length" description="回收站为空" />
    <el-table v-else :data="items" row-key="id">
      <el-table-column prop="title" label="笔记" />
      <el-table-column label="移入时间">
        <template #default="{ row }">{{ new Date(row.deleted_at).toLocaleString('zh-CN') }}</template>
      </el-table-column>
      <el-table-column width="110">
        <template #default="{ row }">
          <el-button :loading="restoring === row.id" :disabled="restoring !== null" @click="restore(row)">恢复</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-if="total > 20" layout="prev, pager, next" :total="total" :page-size="20"
      :current-page="page" :disabled="loading" @current-change="load" />
  </section>
</template>
