import { defineStore } from 'pinia'
import { ref } from 'vue'

interface UserInfo {
  id: string
  username: string
  role: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>('fake_token')
  const user = ref<UserInfo | null>({ id: 'admin', username: 'admin', role: 'admin' })

  function setAuth(accessToken: string, userInfo: UserInfo) {
    token.value = accessToken
    user.value = userInfo
  }

  function logout() {
    token.value = 'fake_token'
    user.value = { id: 'admin', username: 'admin', role: 'admin' }
  }

  function isLoggedIn(): boolean {
    return true
  }

  return { token, user, setAuth, logout, isLoggedIn }
})
