<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getRecommendations, recordPaperInteraction } from '@/request/api'

interface Paper {
  id: string;
  title: string;
  authors: string[];
  year?: number;
  abstract: string;
  pdf_url: string;
  keywords?: string[];
  published_date?: string;
}

const props = defineProps<{
  visible: boolean
  paperData: Paper | null
}>()

const emit = defineEmits(['update:visible'])

const recommendations = ref<Paper[]>([])
const loadingRecommendations = ref(false)
const recommendationError = ref('')

const closeDialog = () => {
  emit('update:visible', false)
}

const fetchRecommendations = async () => {
  if (!props.paperData?.id) return
  
  try {
    loadingRecommendations.value = true
    recommendationError.value = ''
    recommendations.value = []
    
    // Record view interaction
    try {
      await recordPaperInteraction(props.paperData.id, 'view')
    } catch (error) {
      console.error('Failed to record view interaction:', error)
      // Continue even if recording fails
    }
    
    try {
      const paper = await getRecommendations(props.paperData.id)
      recommendations.value = [paper]
    } catch (error) {
      if (error.response?.status === 404) {
        recommendationError.value = '未找到相关推荐论文'
      } else if (error.response?.status === 500) {
        recommendationError.value = '推荐服务暂时不可用'
      } else {
        recommendationError.value = '获取推荐论文失败，请稍后再试'
      }
      console.error('Failed to fetch recommendations:', error)
    }
  } finally {
    loadingRecommendations.value = false
  }
}

watch(() => props.paperData, (newVal) => {
  if (newVal) {
    fetchRecommendations()
  }
}, { immediate: true })
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="closeDialog"
    :title="paperData?.title || '论文详情'"
    width="70%"
    top="5vh"
  >
    <div v-if="paperData" class="paper-detail-dialog">
      <div class="paper-meta">
        <p><strong>作者:</strong> {{ paperData.authors.join(', ') }}</p>
        <p v-if="paperData.published_date"><strong>发表日期:</strong> {{ paperData.published_date }}</p>
        <p v-if="paperData.year"><strong>年份:</strong> {{ paperData.year }}</p>
        <p v-if="paperData.keywords && paperData.keywords.length > 0">
          <strong>关键词:</strong> {{ paperData.keywords.join(', ') }}
        </p>
      </div>

      <div class="paper-abstract">
        <h3>摘要</h3>
        <p>{{ paperData.abstract }}</p>
      </div>

      <div class="paper-pdf">
        <h3>PDF全文</h3>
        <div class="pdf-container">
          <iframe 
            :src="paperData.pdf_url" 
            width="100%" 
            height="500px"
            style="border: 1px solid #ddd; border-radius: 4px;"
            v-if="paperData.pdf_url"
          ></iframe>
          <p v-else>暂无PDF全文</p>
        </div>
      </div>

      <div class="paper-recommendations">
        <h3>相关推荐</h3>
        <div v-if="loadingRecommendations" class="loading">
          <el-icon class="is-loading" size="24">
            <Loading />
          </el-icon>
          <span>加载推荐中...</span>
        </div>
        <div v-else-if="recommendationError" class="error">
          {{ recommendationError }}
        </div>
        <div v-else-if="recommendations.length > 0" class="recommendation-list">
          <div v-for="paper in recommendations" :key="paper.id" class="recommendation-item">
            <h4 @click="emit('update:visible', false); $emit('show-paper', paper.id)">
              {{ paper.title }}
            </h4>
            <p>{{ paper.authors.join(', ') }}</p>
            <p class="abstract-preview">{{ paper.abstract.substring(0, 150) }}...</p>
          </div>
        </div>
        <div v-else class="no-recommendations">
          暂无相关推荐
        </div>
      </div>
    </div>
    <div v-else class="loading">
      <el-icon class="is-loading" size="24">
        <Loading />
      </el-icon>
      <span>加载中...</span>
    </div>
    
    <template #footer>
      <el-button @click="closeDialog">关闭</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.paper-detail-dialog {
  max-height: 70vh;
  overflow-y: auto;
  padding: 0 10px;
}

.paper-meta p {
  margin: 8px 0;
  color: #666;
}

.paper-abstract h3 {
  margin: 20px 0 10px;
  color: #333;
}

.paper-abstract p {
  line-height: 1.6;
  color: #444;
}

.paper-pdf {
  margin-top: 20px;
}

.pdf-container {
  margin-top: 10px;
}

.paper-recommendations {
  margin-top: 30px;
  border-top: 1px solid #eee;
  padding-top: 20px;
}

.recommendation-list {
  margin-top: 15px;
}

.recommendation-item {
  margin-bottom: 20px;
  padding: 10px;
  border-radius: 4px;
  background-color: #f9f9f9;
  cursor: pointer;
  transition: background-color 0.2s;
}

.recommendation-item:hover {
  background-color: #f0f0f0;
}

.recommendation-item h4 {
  margin: 0 0 5px 0;
  color: #1a73e8;
}

.recommendation-item p {
  margin: 5px 0;
  color: #666;
}

.abstract-preview {
  font-size: 0.9em;
  color: #777;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  height: 200px;
  color: #666;
}

.error {
  color: #f56c6c;
  text-align: center;
  padding: 10px;
}

.no-recommendations {
  color: #999;
  text-align: center;
  padding: 10px;
}
</style>
