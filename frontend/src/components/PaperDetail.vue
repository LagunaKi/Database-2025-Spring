<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPaperDetail } from '@/request/api'

interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  abstract: string;
}

const route = useRoute()
const paper = ref<Paper | null>(null)

onMounted(async () => {
  const paperId = route.params.id as string
  try {
    const res = await getPaperDetail(paperId)
    paper.value = res
  } catch (e) {
    console.error(e)
  }
})
</script>

<template>
  <div v-if="paper" class="paper-detail">
    <h1>{{ paper.title }}</h1>
    <p><strong>作者:</strong> {{ paper.authors.join(', ') }}</p>
    <p><strong>年份:</strong> {{ paper.year }}</p>
    <p><strong>摘要:</strong> {{ paper.abstract }}</p>
  </div>
  <div v-else>
    加载中...
  </div>
</template>

<style scoped>
.paper-detail {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
</style>
