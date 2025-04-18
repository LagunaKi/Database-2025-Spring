<script setup lang="ts">
import { reactive, ref } from 'vue';
import type { FormInstance } from 'element-plus';
import { ElMessage } from 'element-plus';
import { ChatWithLLM } from "@/request/api";
import PaperDetail from './PaperDetail.vue';
import HighlightText from './HighlightText.vue';
import MarkdownIt from 'markdown-it';

// 添加类型声明
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

interface Match {
  paper_id: string;
  match_score: number;
  matched_section: string;
  paper?: Paper;
}

const ruleFormRef = ref<FormInstance>();
const isLoading = ref(false);
const md = new MarkdownIt();

const chatForm = reactive({
  prompt: '',
  response: '',
});

const renderMarkdown = (text: string) => {
  // 仅渲染基本Markdown，保留原始文本结构
  md.set({ 
    html: true,
    breaks: true,
    linkify: true,
    typographer: false
  });
  // 移除Markdown渲染中的特殊处理
  return text;
};

const papers = ref<Paper[]>([]);
const matches = ref<Match[]>([]);
const showPaperDetail = ref(false);
const currentPaper = ref<Paper | null>(null);

const viewPaperDetail = (paper: Paper) => {
  currentPaper.value = paper;
  showPaperDetail.value = true;
};



const submitForm = (formEl: FormInstance | undefined) => {
  if (!formEl) return;
  formEl.validate(async (valid) => {
    if (valid) {
      isLoading.value = true;
      try {
        const res = await ChatWithLLM({ prompt: chatForm.prompt });
        
        // 确保matches数据结构正确
        const enrichedMatches = res.matches?.map(match => {
          const paper = res.papers.find(p => p.id === match.paper_id);
          if (!paper) {
            console.warn(`No paper found for match with paper_id: ${match.paper_id}`);
            return null;
          }
          return {
            paper_id: match.paper_id,
            match_score: match.match_score,
            matched_section: match.matched_section,
            paper: {
              id: paper.id,
              title: paper.title,
              authors: paper.authors
            }
          };
        }).filter(match => match !== null) ?? [];
        
        chatForm.response = res.response;
        papers.value = res.papers;
        matches.value = enrichedMatches;
        
        // 调试日志
        console.log('Response:', res.response);
        console.log('Matches:', enrichedMatches);
        console.log('Papers:', res.papers);
      } catch (e) {
        console.log(e);
        ElMessage.error('获取论文信息失败');
      } finally {
        isLoading.value = false;
      }
    }
  });
};
</script>

<template>
  <div class="chat-container">
    <div class="main-content">
      <div class="input-container">
        <el-form
          ref="ruleFormRef"
          :model="chatForm"
          label-width="0"
          class="demo-ruleForm"
          style="width: 100%"
        >
          <h3 style="color: white;">提问：</h3>
          <el-form-item prop="prompt" class="inline-form-item">
            <el-input 
              v-model="chatForm.prompt" 
              type="text" 
              autocomplete="off"
              placeholder="输入你想要搜索并总结的论文"
              style="padding-right: 70px;"
            />
            <el-button 
              style="background-color: burlywood; color: white; position: absolute; right: 0; top: 50%; transform: translateY(-50%);" 
              @click="submitForm(ruleFormRef)"
            >
              搜索
            </el-button>
          </el-form-item>
        </el-form>
      </div>
      <div class="response-box">
        <h3 style="color: white;">回答：</h3>
        <div v-if="isLoading" class="loading-spinner"></div>
        <div 
          v-else-if="chatForm.response && matches"
          class="response-content" 
          style="color: white;"
        >
          <HighlightText 
            :text="renderMarkdown(chatForm.response)"
            :matches="matches ?? []"
          />
        </div>
      </div>
    </div>

    <div class="sidebar">
      <div class="paper-container">
        <h3 style="color: white;">相关论文</h3>
        <el-table :data="papers" style="width: 100%">
          <el-table-column prop="title" label="标题" width="180">
            <template #default="{row}">
              <div>
                {{ row.title }}
                <!-- 仅当匹配度大于0.3时显示匹配度信息 -->
                <template v-if="matches?.length">
                  <div class="match-info">
                    <template v-if="matches.find(m => m?.paper_id === row.id)?.match_score === undefined || 
                      (matches.find(m => m?.paper_id === row.id)?.match_score ?? 0) < 0.3">
                      <el-tag size="small" type="info">相关论文</el-tag>
                    </template>
                    <template v-else>
                      <el-tag size="small" type="success">
                        匹配度: {{ ((matches.find(m => m?.paper_id === row.id)?.match_score ?? 0) * 100).toFixed(0) }}%
                      </el-tag>
                      <div class="match-section">
                        {{ matches.find(m => m?.paper_id === row.id)?.matched_section || '' }}
                      </div>
                    </template>
                  </div>
                </template>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="作者">
            <template #default="{row}">
              {{ row.authors.join(', ') }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button type="primary" @click="viewPaperDetail(scope.row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <PaperDetail 
      :visible="showPaperDetail" 
      :paperData="currentPaper"
      @update:visible="val => showPaperDetail = val"
      @show-paper="viewPaperDetail"
    />
  </div>
</template>

<style scoped>
.chat-container {
  display: flex;
  gap: 20px;
  min-height: 100vh;
  background-image: url('@/assets/images/chat_background.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  position: relative;
}

.highlight:hover {
  background-color: rgba(255, 215, 0, 0.5);
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.3);
}

.highlight-title {
  background-color: rgba(100, 200, 255, 0.3);
  border-bottom: 2px solid #64c8ff;
}

.highlight {
  position: relative;
  display: inline;
}

.highlight .tooltip {
  display: none !important;
  position: absolute;
  bottom: calc(100% + 5px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 300px;
  max-width: 400px;
  padding: 12px;
  background: rgba(30, 30, 30, 0.95) !important;
  color: white !important;
  border-radius: 6px;
  z-index: 1000;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
}

.highlight:hover .tooltip {
  display: block !important;
}

.highlight .tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border-width: 6px;
  border-style: solid;
  border-color: rgba(30, 30, 30, 0.95) transparent transparent transparent;
}

.match-tooltip {
  font-size: 14px;
  line-height: 1.6;
}

.match-tooltip .match-title {
  font-weight: bold;
  margin-bottom: 8px;
  color: #ffd700;
  font-size: 15px;
}

.match-tooltip .match-score {
  color: #fff;
  background: rgba(255, 215, 0, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
  margin-bottom: 8px;
}

.match-tooltip .match-authors {
  color: #ccc;
  font-size: 13px;
  margin-bottom: 4px;
}

.highlight-title {
  background-color: rgba(100, 200, 255, 0.3);
  border-bottom: 2px solid #64c8ff;
  padding: 0 2px;
  border-radius: 2px;
}

.highlight-title:hover {
  background-color: rgba(100, 200, 255, 0.5);
  box-shadow: 0 0 8px rgba(100, 200, 255, 0.3);
}

.main-content {
  flex: 1;
}

.input-container {
  padding: 20px;
  border: 1px solid #ebeef5;
  background-color: rgba(64, 64, 64, 0.8);
  border-radius: 8px;
  margin-bottom: 20px;
}

.inline-form-item {
  display: flex;
  gap: 10px;
}

.inline-form-item .el-form-item__content {
  display: flex;
  gap: 10px;
  flex: 1;
}

.sidebar {
  width: 500px;
}

.paper-container {
  padding: 20px;
  border: 1px solid #ebeef5;
  background-color: rgba(64, 64, 64, 0.8);
  border-radius: 8px;
}

.response-box {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: rgba(64, 64, 64, 0.8);
}

.response-content {
  margin-top: 10px;
  white-space: pre-wrap;
  position: relative;
  overflow: visible;
  z-index: 1;
}

.highlight {
  position: relative;
  background-color: rgba(255, 215, 0, 0.3);
  border-bottom: 1px dashed gold;
  cursor: help;
  z-index: 2;
}

.highlight .tooltip {
  display: none;
  position: absolute;
  bottom: calc(100% + 5px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 300px;
  max-width: 400px;
  padding: 12px;
  background: rgba(30, 30, 30, 0.95);
  color: white;
  border-radius: 6px;
  z-index: 1000;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
}

.highlight:hover .tooltip {
  display: block;
}

.match-info {
  margin-top: 4px;
}

.match-section {
  font-size: 12px;
  color: #ccc;
  margin-top: 2px;
}

.loading-spinner {
  display: block;
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255,255,255,.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 1s ease-in-out infinite;
  margin: 20px auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
