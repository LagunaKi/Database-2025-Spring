<script setup lang="ts">
import { ref } from 'vue'
import { Loading } from '@element-plus/icons-vue'

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

const closeDialog = () => {
  emit('update:visible', false)
}
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
    </div>
    <div v-else class="loading">
      <el-icon class="is-loading" size="24">
        <Loading />
      </el-icon>
      <span>加载中...</span>
    </div>
    
    <template #footer>
      <el-button @click="closeDialog">关闭</el-button>
      <el-button 
        type="primary" 
        v-if="paperData?.pdf_url"
        :href="paperData.pdf_url"
        target="_blank"
      >
        打开PDF
      </el-button>
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

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  height: 200px;
  color: #666;
}
</style>
