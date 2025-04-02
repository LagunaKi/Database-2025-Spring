import axios from 'axios'
import {useUserstore} from '@/store/user'

// 创建axios实例
const request = axios.create({
    baseURL: 'http://localhost:8000',// 后端API基础地址
    timeout: 80000, // 请求超时时间(毫秒)
    withCredentials: true,// 异步请求携带cookie
    headers: {
        'Content-Type': 'application/json',
    }
})
request.defaults.withCredentials = true;
// request拦截器
request.interceptors.request.use(
    request => {
        const userStore=useUserstore()
        if (userStore.token) {
            request.headers.Authorization = `Bearer ${userStore.token}`
        }
        return request
    },
    error => {
        return Promise.reject(error)
    }
)

// response 拦截器
request.interceptors.response.use(
    response => {
        // 对响应数据做点什么
        return response.data
    },
    error => {
        // 对响应错误做点什么
        return Promise.reject(error)
    }
)
export default request