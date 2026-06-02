'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout/app-layout'
import { ProjectCard } from '@/components/project/project-card'
import { NewProjectDialog } from '@/components/project/new-project-dialog'
import {
  useProjectStore,
} from '@/stores/project-store'
import {
  generationApi,
  type Platform,
  type GenerationRequest,
} from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { Loader2, Film, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function DashboardPage() {
  const router = useRouter()
  const { projects, isLoading, error, fetchProjects, createProject, deleteProject } =
    useProjectStore()
  const { startPolling } = useTaskStore()
  const [showNewDialog, setShowNewDialog] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  async function handleCreateProject(params: {
    movie_id: string
    movie_title: string
    style_id: string
    style_name: string
    platform: Platform
  }) {
    const project = await createProject({
      movie_id: params.movie_id,
      movie_title: params.movie_title,
      style_id: params.style_id,
      style_name: params.style_name,
      platform: params.platform,
      status: 'selecting',
      script_segments: [],
      voice_id: 'narrator-male-youth-01',
    })

    if (project) {
      // Start generation
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
        router.push(`/project/${project.project_id}`)
      }
    }
  }

  return (
    <AppLayout
      title="Dashboard"
      action={{ label: 'New Project', onClick: () => setShowNewDialog(true) }}
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <p className="text-red-400 text-sm">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchProjects}>
            Retry
          </Button>
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
