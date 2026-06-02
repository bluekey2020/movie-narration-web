'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout/app-layout'
import { ProjectCard } from '@/components/project/project-card'
import { NewProjectDialog } from '@/components/project/new-project-dialog'
import { useProjectStore } from '@/stores/project-store'
import { generationApi, type Platform, type GenerationRequest } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { Loader2, Film, Plus, ServerOff } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function DashboardPage() {
  const router = useRouter()
  const { projects, isLoading, error, fetchProjects, createProject, deleteProject } =
    useProjectStore()
  const { startPolling } = useTaskStore()
  const [showNewDialog, setShowNewDialog] = useState(false)
  const [backendAvailable, setBackendAvailable] = useState(true)

  useEffect(() => {
    fetchProjects().then(() => {
      // If fetchProjects set an error, backend is likely down
    }).catch(() => {
      setBackendAvailable(false)
    })
  }, [fetchProjects])

  async function handleCreateProject(params: {
    movie_id: string
    movie_title: string
    style_id: string
    style_name: string
    platform: Platform
  }) {
    // Create project locally first (works without backend)
    const project = await createProject({
      movie_id: params.movie_id,
      movie_title: params.movie_title,
      style_id: params.style_id,
      style_name: params.style_name,
      platform: params.platform,
      status: 'draft',
      script_segments: getMockSegments(params.movie_title, params.style_name),
      voice_id: 'narrator-male-youth-01',
    })

    if (!project) return

    // Try to start backend generation (non-blocking — navigate anyway)
    try {
      const genReq: GenerationRequest = {
        movie_id: params.movie_id,
        style: params.style_id,
        platform: params.platform,
        voice_id: 'narrator-male-youth-01',
        mode: 'auto',
      }
      const res = await generationApi.start(genReq)
      if (res.success && res.data) {
        startPolling(res.data.task_id)
      }
    } catch {
      // Backend unavailable — user can still edit the mock script
      console.warn('Backend unavailable, using offline mode')
    }

    router.push(`/project/${project.project_id}`)
  }

  return (
    <AppLayout
      title="Dashboard"
      action={{ label: 'New Project', onClick: () => setShowNewDialog(true) }}
    >
      {/* Backend status banner */}
      {!backendAvailable && !isLoading && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-amber-900/30 border border-amber-800/50 px-4 py-2.5 text-sm text-amber-300">
          <ServerOff className="h-4 w-4 shrink-0" />
          Backend not detected — running in offline mode. Start the backend for AI generation and video export.
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <ServerOff className="h-10 w-10 text-zinc-500" />
          <p className="text-zinc-400 text-sm text-center max-w-md">
            Could not connect to the backend server.
            <br />
            You can still create and edit projects — the AI generation features require the backend.
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={fetchProjects}>
              Retry
            </Button>
            <Button size="sm" onClick={() => setShowNewDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Project
            </Button>
          </div>
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800/50">
            <Film className="h-8 w-8 text-zinc-500" />
          </div>
          <div className="text-center">
            <h2 className="text-lg font-medium">No projects yet</h2>
            <p className="text-sm text-zinc-500 mt-1 max-w-md">
              Create your first movie narration video. Choose a movie, pick a
              style, and let AI do the rest.
            </p>
          </div>
          <Button onClick={() => setShowNewDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create First Project
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.project_id}
              project={project}
              onDelete={deleteProject}
            />
          ))}
        </div>
      )}

      <NewProjectDialog
        open={showNewDialog}
        onOpenChange={setShowNewDialog}
        onCreate={handleCreateProject}
      />
    </AppLayout>
  )
}

/** Generate mock script segments for offline/demo mode */
function getMockSegments(movieTitle: string, styleName: string) {
  return [
    {
      index: 1,
      type: 'hook' as const,
      text: `你有没有想过，为什么《${movieTitle}》能成为影史经典？今天我们用${styleName}风格来解读这部电影。`,
      emotion: 'suspense',
      emphasis_words: ['经典', styleName],
      visual_requirement: { description: '', preferred_source: 'visual_template' as const, scene_hint: '', mood: 'suspense' },
      estimated_duration_sec: 12,
    },
    {
      index: 2,
      type: 'intro' as const,
      text: `《${movieTitle}》讲述了主人公在面对命运挑战时的非凡经历。影片通过细腻的叙事和出色的表演，展现了一幅人性图景。`,
      emotion: 'buildup',
      emphasis_words: ['命运', '人性'],
      visual_requirement: { description: '', preferred_source: 'visual_template' as const, scene_hint: '', mood: 'buildup' },
      estimated_duration_sec: 15,
    },
    {
      index: 3,
      type: 'plot' as const,
      text: '故事的第一个转折点，主人公做出了改变一切的决定。这个情节让人震撼——因为它在真实与虚构之间找到了完美的平衡。',
      emotion: 'tense',
      emphasis_words: ['转折点', '改变一切'],
      visual_requirement: { description: '', preferred_source: 'visual_template' as const, scene_hint: '', mood: 'tense' },
      estimated_duration_sec: 18,
    },
    {
      index: 4,
      type: 'twist' as const,
      text: '然而事情并没有那么简单。就在观众以为一切尘埃落定的时候，真正的高潮才刚刚开始。',
      emotion: 'revelation',
      emphasis_words: ['高潮'],
      visual_requirement: { description: '', preferred_source: 'visual_template' as const, scene_hint: '', mood: 'revelation' },
      estimated_duration_sec: 12,
    },
    {
      index: 5,
      type: 'plot' as const,
      text: '随着故事的推进，人物的命运逐渐清晰。每一个细节都在为最终的结局做铺垫。',
      emotion: 'buildup',
      emphasis_words: ['命运', '结局'],
      visual_requirement: { description: '', preferred_source: 'visual_template' as const, scene_hint: '', mood: 'buildup' },
      estimated_duration_sec: 15,
    },
    {
      index: 6,
      type: 'climax' as const,
      text: '最后的高潮场景，令人屏息。所有的伏笔在这里被回收，所有的情感在这里被释放。',
      emotion: 'climax',
      emphasis_words: ['高潮', '回收'],
      visual_requirement: { description: '', preferred_source: 'visual_template' as const, scene_hint: '', mood: 'climax' },
      estimated_duration_sec: 14,
    },
    {
      index: 7,
      type: 'ending' as const,
      text: `这就是《${movieTitle}》——一部值得反复品味的电影。如果你还没看过，强烈推荐找来原片感受一下。`,
      emotion: 'reflection',
      emphasis_words: ['反复品味', '推荐'],
      visual_requirement: { description: '', preferred_source: 'visual_template' as const, scene_hint: '', mood: 'reflection' },
      estimated_duration_sec: 10,
    },
  ]
}
