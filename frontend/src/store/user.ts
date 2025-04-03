import {defineStore} from "pinia";
import {createPersistedState} from 'pinia-plugin-persistedstate'

export const useUserstore = defineStore(
    'user',
    {
        state() {
            return {
                userName: '',
                token: '',
            }
        },
        persist: {
            key: 'user',
            storage: localStorage,
            paths: ['token', 'userName']
        }
    }
)