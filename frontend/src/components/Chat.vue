<script setup lang="ts">
import { reactive, ref } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ChatWithLLM } from "@/request/api";

const router = useRouter();
const ruleFormRef = ref<FormInstance>();

const chatForm = reactive({
  prompt: '',
  response: '',
});

interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  abstract: string;
}

const papers = ref<Paper[]>([]);

const viewPaperDetail = (paper: Paper) => {
  router.push({ name: 'PaperDetail', params: { id: paper.id } }); //跳转到论文详情页面
};

const submitForm = (formEl: FormInstance | undefined) => {
  if (!formEl) return; //输入为空直接返回
  formEl.validate(async (valid) => {
    if (valid) {
      try {
        const res = await ChatWithLLM({ prompt: chatForm.prompt });
        chatForm.response = res.response;
        papers.value = res.papers;
      } catch (e) {
        console.log(e);
      }
    } else {
      return false;
    }
  });
};

//暴露给外部
defineExpose({
  papers,
  viewPaperDetail,
});
</script>

<template>
  <div class="chat-container">
    <div class="main-content">
      <div class="input-container">
        <el-form
          ref="ruleFormRef"
          :model="chatForm"
          label-width="auto"
          class="demo-ruleForm"
          >
          
          <h3 style="color: white;">提问：</h3>
          <el-form-item  prop="prompt" class="inline-form-item">
            <el-input 
              v-model="chatForm.prompt" 
              type="text" 
              autocomplete="off"
              placeholder="输入你想要搜索并总结的论文"
              style="padding-right: 70px;"
            />
            <el-button style="background-color: burlywood; color: white; position: absolute; right: 0; top: 50%; transform: translateY(-50%);" @click="submitForm(ruleFormRef)">搜索</el-button>
          </el-form-item>
        </el-form>
      </div>
      <div class="response-box">
        <h3 style="color: white;">回答：</h3>
        <div class="response-content" style="color: white;">{{ chatForm.response }}</div>
      </div>
    </div>

    <div class="sidebar">
      <div class="paper-container">
        <h3 style="color: white;">相关论文</h3>
        <el-table :data="papers" style="width: 100%">
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="authors" label="作者" />
        <el-table-column prop="year" label="年份" />
        <el-table-column label="操作">
          <template #default="scope">
            <el-button type="primary" @click="viewPaperDetail(scope.row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </div>
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
}
</style>
