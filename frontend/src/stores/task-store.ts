import { create } from 'zustand'
import { generationApi, type TaskProgress } from '@/lib/api'

interface TaskStore {
  activeTask: TaskProgress | null
  taskHistory: TaskProgress[]
  isPolling: boolean
  pollInterval: ReturnType<typeof setInterval> | null

  startPolling: (taskId: string) => void
  stopPolling: () => void
  clearActiveTask: () => void
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  activeTask: null,
  taskHistory: [],
  isPolling: false,
  pollInterval: null,

  startPolling: (taskId: string) => {
    // Clear any existing poll
    const existing = get().pollInterval
    if (existing) clearInterval(existing)

    // Start polling every 2 seconds
    const interval = setInterval(async () => {
      const res = await generationApi.status(taskId)
      if (res.success && res.data) {
        const task = res.data
        set((state) => ({
          activeTask: task,
          taskHistory:
            task.status === 'completed' || task.status === 'failed'
              ? [...state.taskHistory, task]
              : state.taskHistory,
        }))

        // Stop polling when done
        if (task.status === 'completed' || task.status === 'failed') {
          get().stopPolling()
        }
      }
    }, 2000)

    set({ isPolling: true, pollInterval: interval })
  },

  stopPolling: () => {
    const interval = get().pollInterval
    if (interval) {
      clearInterval(interval)
      set({ isPolling: false, pollInterval: null })
    }
  },

  clearActiveTask: () => set({ activeTask: null }),
}))
