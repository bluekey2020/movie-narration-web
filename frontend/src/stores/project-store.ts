import { create } from 'zustand'
import { projectsApi, type Project, type GenerationRequest } from '@/lib/api'

interface ProjectStore {
  projects: Project[]
  currentProject: Project | null
  isLoading: boolean
  error: string | null

  fetchProjects: () => Promise<void>
  fetchProject: (id: string) => Promise<void>
  createProject: (data: Partial<Project>) => Promise<Project | null>
  updateProject: (id: string, data: Partial<Project>) => Promise<void>
  deleteProject: (id: string) => Promise<void>
  setCurrentProject: (project: Project | null) => void
  clearError: () => void
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  projects: [],
  currentProject: null,
  isLoading: false,
  error: null,

  fetchProjects: async () => {
    set({ isLoading: true, error: null })
    const res = await projectsApi.list()
    if (res.success && res.data) {
      set({ projects: res.data, isLoading: false })
    } else {
      set({ error: res.error || 'Failed to fetch projects', isLoading: false })
    }
  },

  fetchProject: async (id: string) => {
    set({ isLoading: true, error: null })
    const res = await projectsApi.get(id)
    if (res.success && res.data) {
      set({ currentProject: res.data, isLoading: false })
    } else {
      set({ error: res.error || 'Failed to fetch project', isLoading: false })
    }
  },

  createProject: async (data: Partial<Project>) => {
    set({ isLoading: true, error: null })
    const res = await projectsApi.create(data)
    if (res.success && res.data) {
      const projects = [...get().projects, res.data]
      set({ projects, currentProject: res.data, isLoading: false })
      return res.data
    } else {
      set({ error: res.error || 'Failed to create project', isLoading: false })
      return null
    }
  },

  updateProject: async (id: string, data: Partial<Project>) => {
    set({ error: null })
    const res = await projectsApi.update(id, data)
    if (res.success && res.data) {
      const projects = get().projects.map((p) =>
        p.project_id === id ? res.data! : p
      )
      set({
        projects,
        currentProject: get().currentProject?.project_id === id
          ? res.data
          : get().currentProject,
      })
    } else {
      set({ error: res.error || 'Failed to update project' })
    }
  },

  deleteProject: async (id: string) => {
    set({ error: null })
    const res = await projectsApi.delete(id)
    if (res.success) {
      const projects = get().projects.filter((p) => p.project_id !== id)
      set({
        projects,
        currentProject:
          get().currentProject?.project_id === id
            ? null
            : get().currentProject,
      })
    } else {
      set({ error: res.error || 'Failed to delete project' })
    }
  },

  setCurrentProject: (project) => set({ currentProject: project }),
  clearError: () => set({ error: null }),
}))
