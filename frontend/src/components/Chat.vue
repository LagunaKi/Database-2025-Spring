<script setup lang="ts">
import {reactive, ref} from 'vue'
import type {FormInstance, FormRules} from 'element-plus'
import {useRouter} from 'vue-router'
import {ElMessage} from 'element-plus'
import {ChatWithLLM} from "@/request/api";
const router = useRouter()

const ruleFormRef = ref<FormInstance>()

const chatForm = reactive({
  prompt: '',
  response: '',
})

const submitForm = (formEl: FormInstance | undefined) => {
  if (!formEl) return
  formEl.validate(async (valid) => {
    if (valid) {
      try {
        let res = await ChatWithLLM({
          prompt: chatForm.prompt
        })
        chatForm.response = res.response
      } catch (e) {
        console.log(e)
      }
    } else {
      return false
    }
  })
}


</script>

<template>
  <el-form
      ref="ruleFormRef"
      :model="chatForm"
      style="max-width: 600px"
      label-width="auto"
      class="demo-ruleForm"
  >

    <el-form-item label="提问" prop="prompt">
      <el-input v-model="chatForm.prompt" type="text" autocomplete="off"/>
    </el-form-item>

    <el-form-item label="回答" prop="response">
      <el-input v-model="chatForm.response" type="text" autocomplete="off"/>
    </el-form-item>

    <el-form-item>
      <el-button type="success" @click="submitForm(ruleFormRef)"
      >发送
      </el-button
      >
    </el-form-item>

  </el-form>
</template>

<style scoped>


</style>