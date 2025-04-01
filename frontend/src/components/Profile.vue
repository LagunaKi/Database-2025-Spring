<script setup lang="ts">
import {GetUserInfoByUserName} from "@/request/api";
import {ElMessage} from "element-plus";
import {onBeforeMount, ref} from "vue";
import {useUserstore} from '@/store/user'
import {useRoute} from "vue-router";

const userStore=useUserstore()
const route = useRoute()

let user = ref({
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  avatar: 'https://tse4-mm.cn.bing.net/th/id/OIP-C.ffVjXyf76-70IQYd75H7wgAAAA?rs=1&pid=ImgDetMain', // 假设的头像URL
})

async function getUserInfo() {
  try {
    let username = userStore.userName
    console.log(route.params)
    if ('username' in route.params) {
      console.log(route.params.username)
      username = route.params.username as string
    }
    let res = await GetUserInfoByUserName({
      userName: username
    })
    console.log(res)
    user.value.username = res.username
    if (res.email === "")
      user.value.email = res.first_name + res.last_name + "@example.com"
    else
      user.value.email = res.email
    user.value.first_name = res.first_name
    user.value.last_name = res.last_name
  } catch (e) {
    console.log(e)
    ElMessage.error('个人信息查询失败')
  }
}

onBeforeMount(() => {
  getUserInfo()
});


</script>

<template>
  <div class="user-profile">
    <img :src="user.avatar" alt="User Avatar" class="avatar"/>
    <h2>{{ user.username }}</h2>
    <p><strong>Full Name:</strong> {{ user.first_name }} {{ user.last_name }}</p>
    <p><strong>Email:</strong> {{ user.email }}</p>
  </div>
</template>

<style scoped>
.user-profile {
  max-width: 300px;
  margin: 20px auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 10px;
  text-align: center;
}

.user-profile .avatar {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  margin-bottom: 20px;
}
</style>