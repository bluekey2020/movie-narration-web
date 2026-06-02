import { create } from 'zustand'
import { authApi, type User, type LoginRequest, type RegisterRequest } from '@/lib/api'

interface UserStore {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  login: (data: LoginRequest) => Promise<boolean>
  register: (data: RegisterRequest) => Promise<boolean>
  logout: () => void
  fetchMe: () => Promise<void>
  clearError: () => void
}

export const useUserStore = create<UserStore>((set, get) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('token') : null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (data: LoginRequest) => {
    set({ isLoading: true, error: null })
    const res = await authApi.login(data)
    if (res.success && res.data) {
      localStorage.setItem('token', res.data.token)
      set({
        user: res.data.user,
        token: res.data.token,
        isAuthenticated: true,
        isLoading: false,
      })
      return true
    } else {
      set({ error: res.error || 'Login failed', isLoading: false })
      return false
    }
  },

  register: async (data: RegisterRequest) => {
    set({ isLoading: true, error: null })
    const res = await authApi.register(data)
    if (res.success && res.data) {
      localStorage.setItem('token', res.data.token)
      set({
        user: res.data.user,
        token: res.data.token,
        isAuthenticated: true,
        isLoading: false,
      })
      return true
    } else {
      set({ error: res.error || 'Registration failed', isLoading: false })
      return false
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: null, isAuthenticated: false })
  },

  fetchMe: async () => {
    const token = get().token
    if (!token) return

    set({ isLoading: true })
    const res = await authApi.me()
    if (res.success && res.data) {
      set({ user: res.data, isAuthenticated: true, isLoading: false })
    } else {
      // Token might be expired
      localStorage.removeItem('token')
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      })
    }
  },

  clearError: () => set({ error: null }),
}))
