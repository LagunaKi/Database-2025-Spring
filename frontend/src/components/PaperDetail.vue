<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPaperDetail } from '@/request/api'

interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  abstract: string;
  pdf_url: string;
  keywords?: string[];
  published_date?: string;
}

const route = useRoute()
const router = useRouter()
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

const goBack = () => {
  router.go(-1)
}
</script>

<template>
  <div v-if="paper" class="paper-detail-container">
    <el-button type="primary" @click="goBack" class="back-button">返回</el-button>
    
    <div class="paper-header">
      <h1>{{ paper.title }}</h1>
      <div class="paper-meta">
        <p><strong>作者:</strong> {{ paper.authors.join(', ') }}</p>
        <p v-if="paper.published_date"><strong>发表日期:</strong> {{ paper.published_date }}</p>
        <p v-if="paper.year"><strong>年份:</strong> {{ paper.year }}</p>
        <p v-if="paper.keywords && paper.keywords.length > 0">
          <strong>关键词:</strong> {{ paper.keywords.join(', ') }}
        </p>
      </div>
    </div>

    <div class="paper-content">
      <div class="paper-abstract">
        <h3>摘要</h3>
        <p>{{ paper.abstract }}</p>
      </div>

      <div class="paper-pdf">
        <h3>PDF全文</h3>
        <iframe 
          :src="paper.pdf_url" 
          width="100%" 
          height="600px"
          style="border: 1px solid #ddd; border-radius: 4px;"
          v-if="paper.pdf_url"
        ></iframe>
        <p v-else>暂无PDF全文</p>
      </div>
    </div>
  </div>
  <div v-else class="loading">
    <el-icon class="is-loading" size="24">
      <Loading />
    </el-icon>
    <span>加载中...</span>
  </div>
</template>

<style scoped>
.paper-detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.back-button {
  margin-bottom: 20px;
}

.paper-header {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.paper-header h1 {
  font-size: 24px;
  margin-bottom: 15px;
  color: #333;
}

.paper-meta p {
  margin: 8px 0;
  color: #666;
}

.paper-content {
  display: flex;
  gap: 30px;
}

.paper-abstract {
  flex: 1;
}

.paper-pdf {
  flex: 1;
}

.paper-abstract h3,
.paper-pdf h3 {
  margin-bottom: 15px;
  color: #333;
  font-size: 18px;
}

.paper-abstract p {
  line-height: 1.6;
  color: #444;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  height: 200px;
  color: #666;
}
</style>
