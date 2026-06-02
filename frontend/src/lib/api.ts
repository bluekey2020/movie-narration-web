/** API 客户端 —— 前端与后端通信 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export const api = {
  movies: {
    list: (genre?: string) => request<any>(`/movies/${genre ? `?genre=${genre}` : ''}`),
    get: (id: string) => request<any>(`/movies/${id}`),
    scenes: (id: string) => request<any>(`/movies/${id}/scenes`),
  },
  styles: {
    list: () => request<any>('/styles/'),
    get: (id: string) => request<any>(`/styles/${id}`),
  },
  projects: {
    create: (data: any) => request<any>('/projects/', { method: 'POST', body: JSON.stringify(data) }),
    list: () => request<any>('/projects/'),
    get: (id: string) => request<any>(`/projects/${id}`),
  },
  generation: {
    start: (data: any) => request<any>('/generation/start', { method: 'POST', body: JSON.stringify(data) }),
    status: (taskId: string) => request<any>(`/generation/task/${taskId}/status`),
  },
}
