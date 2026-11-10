import { defineStore } from 'pinia'
import { authApi } from '@/api'
import { TOKEN_KEY } from '@/api/http'
import type { AdminProfile } from '@/api/types'

const LEVEL = { viewer: 1, admin: 2, super_admin: 3 } as const

export const useAuthStore = defineStore('auth', {
  state: () => ({ token: localStorage.getItem(TOKEN_KEY) || '', profile: null as AdminProfile | null }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    canWrite: (s) => !!s.profile && LEVEL[s.profile.role] >= LEVEL.admin,
    isSuper: (s) => s.profile?.role === 'super_admin',
  },
  actions: {
    async login(username: string, password: string) {
      const res = await authApi.login(username, password)
      this.token = res.access_token
      this.profile = res.profile
      localStorage.setItem(TOKEN_KEY, res.access_token)
    },
    async fetchMe() {
      const res = await authApi.me()
      if (res.principal_type !== 'admin') throw new Error('not admin')
      this.profile = res.profile
    },
    logout() {
      this.token = ''
      this.profile = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
