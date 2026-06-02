// ===== Base types =====

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: {
    total: number
    page: number
    limit: number
  }
}

// ===== Movie types =====

export interface MovieScene {
  name: string
  timestamp: string
  tags: string[]
}

export interface Movie {
  movie_id: string
  title: string
  year: number
  genre: string[]
  rating: number
  duration: number
  poster_url?: string
  plot_summary: string
  key_scenes: MovieScene[]
  character_list: string[]
  hot_topics: string[]
}

// ===== Style types =====

export interface StyleFingerprint {
  style_id: string
  name: string
  description: string
  narrative_rhythm: Record<string, unknown>
  hook_strategy: Record<string, unknown>
  emotion_curve: Record<string, unknown>
  vocabulary_style: Record<string, unknown>
  voice_config: Record<string, unknown>
  bgm_strategy: Record<string, unknown>
  visual_style: Record<string, unknown>
  platform_adaptations: Record<string, Record<string, unknown>>
}

// ===== Project types =====

export type ProjectStatus =
  | 'draft'
  | 'selecting'
  | 'scripting'
  | 'voicing'
  | 'composing'
  | 'reviewing'
  | 'completed'
  | 'failed'

export type Platform = 'douyin' | 'bilibili' | 'kuaishou' | 'xiaohongshu'

export interface ScriptSegment {
  index: number
  type: 'hook' | 'intro' | 'plot' | 'twist' | 'climax' | 'ending'
  text: string
  emotion: string
  emphasis_words: string[]
  visual_requirement: {
    description: string
    preferred_source: 'original_clip' | 'visual_template' | 'ai_generated'
    scene_hint: string
    mood: string
  }
  estimated_duration_sec: number
}

export interface Project {
  project_id: string
  movie_id: string
  movie_title: string
  style_id: string
  style_name: string
  platform: Platform
  status: ProjectStatus
  script_segments: ScriptSegment[]
  voice_id: string
  output_url?: string
  created_at: string
  updated_at: string
}

// ===== Task types =====

export type TaskStage =
  | 'script_generation'
  | 'scene_matching'
  | 'voice_generation'
  | 'bgm_planning'
  | 'video_composition'
  | 'done'

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface TaskProgress {
  task_id: string
  project_id: string
  stage: TaskStage
  status: TaskStatus
  progress: number
  message: string
  error?: string
}

// ===== Auth types =====

export interface User {
  user_id: string
  email: string
  display_name: string
  plan: 'free' | 'personal' | 'professional' | 'team'
  credits_remaining: number
  monthly_videos_used: number
  monthly_videos_limit: number
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  display_name: string
}

// ===== Generation request =====

export interface GenerationRequest {
  movie_id: string
  style: string
  platform: Platform
  voice_id: string
  mode: 'auto' | 'manual_review'
}

// ===== API Client =====

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE}${API_PREFIX}${path}`
  const token =
    typeof window !== 'undefined' ? localStorage.getItem('token') : null

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(url, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const errorBody = await res
      .json()
      .catch(() => ({ detail: res.statusText }))
    return {
      success: false,
      error: errorBody.detail || `HTTP ${res.status}`,
    }
  }

  return res.json()
}

// ===== Movies API =====

export const moviesApi = {
  list: (params?: { genre?: string; search?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.genre) searchParams.set('genre', params.genre)
    if (params?.search) searchParams.set('search', params.search)
    const qs = searchParams.toString()
    return request<Movie[]>(`/movies/${qs ? `?${qs}` : ''}`)
  },
  get: (id: string) => request<Movie>(`/movies/${id}`),
  scenes: (id: string) => request<MovieScene[]>(`/movies/${id}/scenes`),
}

// ===== Styles API =====

export const stylesApi = {
  list: () => request<StyleFingerprint[]>('/styles/'),
  get: (id: string) => request<StyleFingerprint>(`/styles/${id}`),
}

// ===== Projects API =====

export const projectsApi = {
  list: () => request<Project[]>('/projects/'),
  get: (id: string) => request<Project>(`/projects/${id}`),
  create: (data: Partial<Project>) =>
    request<Project>('/projects/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<Project>) =>
    request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),
}

// ===== Multi-platform export types =====

export interface ExportAllRequest {
  project_id: string
  platforms: Platform[]
  movie_id?: string
  style?: string
  voice_id?: string
  mode?: 'auto' | 'manual_review'
}

export interface ExportTaskInfo {
  task_id: string
  celery_task_id: string
}

export interface ExportAllResponse {
  success: boolean
  tasks: Record<Platform, ExportTaskInfo>
  message?: string
}

// ===== Generation API =====

export const generationApi = {
  start: (data: GenerationRequest) =>
    request<TaskProgress>('/generation/start', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  status: (taskId: string) =>
    request<TaskProgress>(`/generation/task/${taskId}/status`),
  exportAll: (data: ExportAllRequest) =>
    request<ExportAllResponse>('/generation/export-all', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}

// ===== Auth API =====

export const authApi = {
  login: (data: LoginRequest) =>
    request<{ token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  register: (data: RegisterRequest) =>
    request<{ token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  me: () => request<User>('/auth/me'),
}
