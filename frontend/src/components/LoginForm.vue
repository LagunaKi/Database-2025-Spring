<script setup lang="ts">

import {reactive, ref} from 'vue'
import type {FormInstance, FormRules} from 'element-plus'
import {useRouter} from 'vue-router'
import {useUserstore} from '@/store/user'

const userStore=useUserstore()
const router = useRouter()

const ruleFormRef = ref<FormInstance>()

const ruleForm = reactive({
  userName: '',
  password: ''
})


const checkUserName = (rule: any, value: any, callback: any) => {
  if (value === '') {
    return callback(new Error('请输入用户名'))
  } else {
    callback()
  }
}

const checkPassword = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('请输入密码'))
  } else {
    callback()
  }
}

const rules = reactive<FormRules<typeof ruleForm>>({
  userName: [{validator: checkUserName, trigger: 'blur'}],
  password: [{validator: checkPassword, trigger: 'blur'}],
})
import {LoginApi} from "@/request/api";
import {ElMessage} from 'element-plus'

const submitForm = (formEl: FormInstance | undefined) => {
  if (!formEl) return
  formEl.validate(async (valid) => {
    if (valid) {
      try {
        let res = await LoginApi({
          username: ruleForm.userName,
          password: ruleForm.password
        })
        console.log('Login response:', res)
        if (res && res.access_token) {
          ElMessage.success('登陆成功')
          userStore.token = res.access_token
          userStore.userName = ruleForm.userName
          try {
            await router.push({ name: 'IndexMain', params: { userName: ruleForm.userName } })
          } catch (routerError) {
            console.error('Router error:', routerError)
            ElMessage.warning('登录成功，但跳转页面失败')
          }
        } else {
          console.error('Invalid response structure:', res)
          ElMessage.error('登陆失败：无效的响应格式')
        }
      } catch (e) {
        console.error('Login error:', e)
        ElMessage.error('登陆失败，请检查用户名和密码')
      }
    } else {
      ElMessage.error('登陆失败，未输入用户名和密码')
      return false
    }
  })
}

function jumpToRegister() {
  router.push('/register')
}

</script>

<template>
  <el-form
      ref="ruleFormRef"
      :model="ruleForm"
      :rules="rules"
      style="max-width: 600px"
      label-width="auto"
      class="demo-ruleForm"
  >

    <el-form-item label="用户名" prop="userName">
      <el-input v-model="ruleForm.userName" type="text" autocomplete="off"/>
    </el-form-item>

    <el-form-item label="密码" prop="password">
      <el-input v-model="ruleForm.password" type="password" autocomplete="off"/>
    </el-form-item>

    <el-form-item>
      <el-button type="primary" @click="submitForm(ruleFormRef)"
      >登录
      </el-button
      >
      <el-button type="success" @click="jumpToRegister()"
      >注册
      </el-button
      >
    </el-form-item>

  </el-form>
</template>

<style scoped>

</style>