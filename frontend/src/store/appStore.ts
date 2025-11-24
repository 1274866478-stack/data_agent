import { create } from 'zustand'

interface AppState {
  loading: boolean
  error: string | null
  theme: 'light' | 'dark'
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setTheme: (theme: 'light' | 'dark') => void
  clearError: () => void
}

export const useAppStore = create<AppState>((set) => ({
  loading: false,
  error: null,
  theme: 'light',

  setLoading: (loading: boolean) => set({ loading }),

  setError: (error: string | null) => set({ error }),

  setTheme: (theme: 'light' | 'dark') => {
    set({ theme })
    localStorage.setItem('theme', theme)
  },

  clearError: () => set({ error: null }),
}))