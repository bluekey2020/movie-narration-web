'use client'

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout/app-layout'
import { useProjectStore } from '@/stores/project-store'
import { useTaskStore } from '@/stores/task-store'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Loader2,
  FileText,
  Mic,
  Video,
  Download,
  AlertCircle,
} from 'lucide-react'
import type { ScriptSegment } from '@/lib/api'

const STAGE_ORDER = [
  'script_generation',
  'scene_matching',
  'voice_generation',
  'bgm_planning',
  'video_composition',
  'done',
] as const

const STAGE_LABELS: Record<string, string> = {
  script_generation: 'Generating Script',
  scene_matching: 'Matching Scenes',
  voice_generation: 'Generating Voice',
  bgm_planning: 'Planning BGM',
  video_composition: 'Composing Video',
  done: 'Complete',
}

const EMOTION_COLORS: Record<string, string> = {
  suspense: 'bg-red-900/50 text-red-300',
  shock_curiosity: 'bg-orange-900/50 text-orange-300',
  buildup: 'bg-blue-900/50 text-blue-300',
  tense: 'bg-purple-900/50 text-purple-300',
  revelation: 'bg-yellow-900/50 text-yellow-300',
  climax: 'bg-red-900/50 text-red-300',
  reflection: 'bg-green-900/50 text-green-300',
  hope: 'bg-emerald-900/50 text-emerald-300',
  comedy: 'bg-amber-900/50 text-amber-300',
}

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { currentProject, isLoading, fetchProject } = useProjectStore()
  const { activeTask } = useTaskStore()

  useEffect(() => {
    if (id) fetchProject(id)
  }, [id, fetchProject])

  if (isLoading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
        </div>
      </AppLayout>
    )
  }

  if (!currentProject) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <AlertCircle className="h-8 w-8 text-zinc-500" />
          <p className="text-zinc-400">Project not found</p>
          <Button variant="outline" size="sm" onClick={() => router.push('/dashboard')}>
            Back to Dashboard
          </Button>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout title={currentProject.movie_title}>
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Progress indicator */}
        {activeTask && activeTask.project_id === id && (
          <Card className="border-zinc-800 bg-zinc-900">
            <CardContent className="p-4">
              <div className="flex items-center gap-4">
                <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">
                      {STAGE_LABELS[activeTask.stage] || activeTask.stage}
                    </span>
                    <span className="text-xs text-zinc-500">
                      {activeTask.progress}%
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-blue-500 transition-all duration-500"
                      style={{ width: `${activeTask.progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-zinc-500 mt-1.5">
                    {activeTask.message}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stage progress dots */}
        <div className="flex items-center gap-2">
          {STAGE_ORDER.map((stage, i) => {
            const isActive = activeTask?.stage === stage
            const isPast =
              activeTask &&
              STAGE_ORDER.indexOf(activeTask.stage) > i
            const isCurrent = isActive
            return (
              <div key={stage} className="flex items-center gap-2">
                <div
                  className={`h-2 w-2 rounded-full ${
                    isPast
                      ? 'bg-green-500'
                      : isCurrent
                        ? 'bg-blue-500 animate-pulse'
                        : 'bg-zinc-700'
                  }`}
                />
                {i < STAGE_ORDER.length - 1 && (
                  <div
                    className={`h-px w-6 ${
                      isPast ? 'bg-green-500/50' : 'bg-zinc-700'
                    }`}
                  />
                )}
              </div>
            )
          })}
          <span className="text-xs text-zinc-500 ml-2">
            {STAGE_LABELS[activeTask?.stage || 'script_generation']}
          </span>
        </div>

        {/* Workbench tabs */}
        <Tabs defaultValue="script" className="w-full">
          <TabsList className="bg-zinc-900 border border-zinc-800">
            <TabsTrigger value="script" className="gap-2">
              <FileText className="h-4 w-4" />
              Script
            </TabsTrigger>
            <TabsTrigger value="voice" className="gap-2">
              <Mic className="h-4 w-4" />
              Voice
            </TabsTrigger>
            <TabsTrigger value="export" className="gap-2">
              <Download className="h-4 w-4" />
              Export
            </TabsTrigger>
          </TabsList>

          {/* Script Tab */}
          <TabsContent value="script" className="space-y-4 mt-4">
            {currentProject.script_segments.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-500">
                <FileText className="h-10 w-10" />
                <p className="text-sm">
                  {activeTask
                    ? 'Script is being generated...'
                    : 'Script generation has not started yet'}
                </p>
              </div>
            ) : (
              currentProject.script_segments.map((seg: ScriptSegment) => (
                <Card
                  key={seg.index}
                  className="border-zinc-800 bg-zinc-900"
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-xs text-zinc-600 font-mono">
                        Seg {seg.index}
                      </span>
                      <span className="text-xs text-zinc-600">
                        {seg.type}
                      </span>
                      <Badge
                        className={
                          EMOTION_COLORS[seg.emotion] || 'bg-zinc-800'
                        }
                      >
                        {seg.emotion}
                      </Badge>
                      <span className="text-xs text-zinc-600 ml-auto">
                        ~{seg.estimated_duration_sec}s
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed">{seg.text}</p>
                    {seg.emphasis_words.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {seg.emphasis_words.map((word) => (
                          <Badge
                            key={word}
                            variant="outline"
                            className="text-xs"
                          >
                            {word}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          {/* Voice Tab */}
          <TabsContent value="voice" className="mt-4">
            <Card className="border-zinc-800 bg-zinc-900">
              <CardContent className="p-6 text-center">
                <Mic className="h-10 w-10 text-zinc-500 mx-auto mb-3" />
                <p className="text-sm text-zinc-400">
                  Voice generation controls will appear here
                </p>
                <p className="text-xs text-zinc-600 mt-1">
                  Once the script is ready, you can select voice characters and
                  adjust parameters
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Export Tab */}
          <TabsContent value="export" className="mt-4">
            <Card className="border-zinc-800 bg-zinc-900">
              <CardContent className="p-6 text-center">
                {currentProject.output_url ? (
                  <div className="space-y-4">
                    <Video className="h-10 w-10 text-green-400 mx-auto" />
                    <p className="text-sm text-zinc-300">
                      Your video is ready!
                    </p>
                    <a
                      href={currentProject.output_url}
                      download
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Button>
                        <Download className="h-4 w-4 mr-2" />
                        Download Video
                      </Button>
                    </a>
                  </div>
                ) : (
                  <>
                    <Video className="h-10 w-10 text-zinc-500 mx-auto mb-3" />
                    <p className="text-sm text-zinc-400">
                      Video export will be available here
                    </p>
                    <p className="text-xs text-zinc-600 mt-1">
                      The video is being composed. You can preview and download
                      it once ready.
                    </p>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  )
}
