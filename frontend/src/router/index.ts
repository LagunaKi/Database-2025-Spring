import {createRouter, createWebHistory} from "vue-router";

import Login from '@/pages/Login.vue';
import Index from "@/pages/Index.vue";
import Test from "@/pages/Test.vue";
import CheckUserInfo from "@/components/CheckUserInfo.vue";
import Profile from "@/components/Profile.vue";
import AddUser from "@/components/AddUser.vue";
import Chat from "@/components/Chat.vue";
import Register from "@/pages/Register.vue";

import PaperDetail from '@/components/PaperDetail.vue';

const routes =
    [
        {
            path: '/',
            name: 'Login',
            component: Login
        },
        {
            path: '/register',
            name: 'Register',
            component: Register
        },
        {
            path: '/index',
            name: 'Index',
            component: Index,
            children: [
                {
                    path: '',
                    name:'IndexMain',
                    component: Profile,
                },
                {
                    path: 'checkUserInfo/:username',
                    name: 'checkUserDetail',
                    component: Profile,
                    props: true
                },
                {
                    path: 'checkUserInfo',
                    component: CheckUserInfo,
                },
                {
                    path: 'addUser',
                    component: AddUser,
                },
                {
                    path: 'chat',
                    component: Chat,
                },
            ]

        },
        {
            path: '/test',
            name: 'Test',
            component: Test
        },
        {
            path: '/paper/:id',
            name: 'PaperDetail',
            component: PaperDetail,
            props: true
        }
    ];

const router = createRouter({
    history: createWebHistory(),
    routes
});

export default router;
