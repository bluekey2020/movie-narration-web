'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Loader2,
  Download,
  Video,
  CheckCircle2,
  XCircle,
  Monitor,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { generationApi, type Platform, type TaskProgress, type ExportTaskInfo } from '@/lib/api'

// ===== Platform display config =====

interface PlatformInfo {
  name: string
  label: string
  aspectRatio: string
  resolution: string
}

const PLATFORM_INFO: Record<Platform, PlatformInfo> = {
  douyin: {
    name: 'douyin',
    label: '抖音',
    aspectRatio: '9:16',
    resolution: '1080x1920',
  },
  bilibili: {
    name: 'bilibili',
    label: 'B站',
    aspectRatio: '16:9',
    resolution: '1920x1080',
  },
  kuaishou: {
    name: 'kuaishou',
    label: '快手',
    aspectRatio: '9:16',
    resolution: '1080x1920',
  },
  xiaohongshu: {
    name: 'xiaohongshu',
    label: '小红书',
    aspectRatio: '3:4',
    resolution: '1080x1440',
  },
}

// ===== Per-platform task state =====

interface PlatformTaskState {
  taskId: string
  celeryTaskId: string
  status: TaskProgress['status']
  progress: number
  stage: string
  message: string
  videoUrl?: string
  error?: string
}

// ===== Props =====

interface PlatformExportPanelProps {
  projectId: string
  movieId?: string
  style?: string
  voiceId?: string
  hasVideo?: boolean
  videoUrl?: string
}

// ===== Component =====

export function PlatformExportPanel({
  projectId,
  movieId,
  style,
  voiceId,
  hasVideo,
  videoUrl,
}: PlatformExportPanelProps) {
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<Platform>>(new Set())
  const [platformTasks, setPlatformTasks] = useState<Record<Platform, PlatformTaskState | null>>(
    {} as Record<Platform, PlatformTaskState | null>
  )
  const [isExporting, setIsExporting] = useState(false)
  const pollIntervals = useRef<Record<string, ReturnType<typeof setInterval>>>({})

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollIntervals.current).forEach(clearInterval)
    }
  }, [])

  // Toggle a platform selection
  const togglePlatform = useCallback((platform: Platform) => {
    if (isExporting) return
    setSelectedPlatforms((prev) => {
      const next = new Set(prev)
      if (next.has(platform)) {
        next.delete(platform)
      } else {
        next.add(platform)
      }
      return next
    })
  }, [isExporting])

  // Select all platforms
  const selectAll = useCallback(() => {
    if (isExporting) return
    setSelectedPlatforms(
      new Set(['douyin', 'bilibili', 'kuaishou', 'xiaohongshu'] as Platform[])
    )
  }, [isExporting])

  // Clear all selections
  const clearAll = useCallback(() => {
    if (isExporting) return
    setSelectedPlatforms(new Set())
  }, [isExporting])

  // Start polling a single task
  const startPollingTask = useCallback((platform: Platform, taskId: string) => {
    // Clear existing poll for this platform
    const existing = pollIntervals.current[platform]
    if (existing) clearInterval(existing)

    const interval = setInterval(async () => {
      const res = await generationApi.status(taskId)
      if (!res.success || !res.data) return

      const data = res.data
      setPlatformTasks((prev) => ({
        ...prev,
        [platform]: {
          taskId: taskId,
          celeryTaskId: '',
          status: data.status,
          progress: data.progress,
          stage: data.stage,
          message: data.message,
          videoUrl: data.status === 'completed' ? `/output/${projectId}_${platform}.mp4` : undefined,
          error: data.status === 'failed' ? data.error || 'Unknown error' : undefined,
        },
      }))

      if (data.status === 'completed' || data.status === 'failed') {
        clearInterval(interval)
        delete pollIntervals.current[platform]
      }
    }, 2000)

    pollIntervals.current[platform] = interval
  }, [projectId])

  // Start export for selected platforms
  const handleExport = useCallback(async () => {
    if (selectedPlatforms.size === 0 || isExporting) return

    setIsExporting(true)
    const platforms = Array.from(selectedPlatforms)

    // Initialize task states as pending
    const initialTasks: Record<Platform, PlatformTaskState | null> = { ...platformTasks }
    for (const p of platforms) {
      initialTasks[p] = {
        taskId: '',
        celeryTaskId: '',
        status: 'pending',
        progress: 0,
        stage: 'script_generation',
        message: 'Queued...',
      }
    }
    setPlatformTasks(initialTasks)

    try {
      const res = await generationApi.exportAll({
        project_id: projectId,
        platforms,
        movie_id: movieId,
        style,
        voice_id: voiceId,
      })

      if (!res.success) {
        // Mark all as failed
        const failedTasks: Record<Platform, PlatformTaskState | null> = { ...initialTasks }
        for (const p of platforms) {
          failedTasks[p] = {
            taskId: '',
            celeryTaskId: '',
            status: 'failed',
            progress: 0,
            stage: 'done',
            message: res.error || 'Export failed',
            error: res.error || 'Export failed',
          }
        }
        setPlatformTasks(failedTasks)
        setIsExporting(false)
        return
      }

      // Start polling each dispatched task
      const tasks = (res.data as { tasks: Record<Platform, ExportTaskInfo> } | undefined)?.tasks || {}
      for (const [platform, taskInfo] of Object.entries(tasks) as [Platform, ExportTaskInfo][]) {
        if (taskInfo.task_id) {
          setPlatformTasks((prev) => ({
            ...prev,
            [platform]: {
              ...(prev[platform] as PlatformTaskState),
              taskId: taskInfo.task_id,
              celeryTaskId: taskInfo.celery_task_id,
              status: 'running',
              message: 'Dispatched',
            },
          }))
          startPollingTask(platform, taskInfo.task_id)
        }
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Network error'
      const failedTasks: Record<Platform, PlatformTaskState | null> = { ...platformTasks }
      for (const p of platforms) {
        failedTasks[p] = {
          taskId: '',
          celeryTaskId: '',
          status: 'failed',
          progress: 0,
          stage: 'done',
          message: 'Export request failed',
          error: message,
        }
      }
      setPlatformTasks(failedTasks)
    } finally {
      setIsExporting(false)
    }
  }, [selectedPlatforms, isExporting, platformTasks, projectId, movieId, style, voiceId, startPollingTask])

  // Check if any task is still active
  const hasActiveTasks = Object.values(platformTasks).some(
    (t) => t && (t.status === 'pending' || t.status === 'running')
  )

  // Check if all selected are complete
  const allSelectedComplete =
    selectedPlatforms.size > 0 &&
    Array.from(selectedPlatforms).every((p) => {
      const t = platformTasks[p]
      return t && t.status === 'completed'
    })

  return (
    <Card className="border-zinc-800 bg-zinc-900">
      <CardHeader>
        <CardTitle className="text-zinc-100">Multi-Platform Export</CardTitle>
        <CardDescription>
          Export your video to multiple platforms with platform-adapted scripts,
          subtitles, and resolutions.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* ===== Platform selection chips ===== */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-500 uppercase tracking-wider">
              Select Platforms
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={selectAll}
                disabled={isExporting}
                className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors disabled:opacity-40"
              >
                All
              </button>
              <span className="text-zinc-700">|</span>
              <button
                onClick={clearAll}
                disabled={isExporting}
                className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors disabled:opacity-40"
              >
                Clear
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {(Object.entries(PLATFORM_INFO) as [Platform, PlatformInfo][]).map(
              ([key, info]) => {
                const isSelected = selectedPlatforms.has(key)
                const task = platformTasks[key]
                const isComplete = task?.status === 'completed'
                const isFailed = task?.status === 'failed'

                return (
                  <button
                    key={key}
                    onClick={() => togglePlatform(key)}
                    disabled={isExporting || isComplete}
                    className={cn(
                      'relative inline-flex items-center gap-2 rounded-lg border px-3 py-2 transition-all',
                      'text-sm font-medium',
                      'disabled:cursor-not-allowed',
                      isSelected
                        ? 'border-blue-500/50 bg-blue-500/10 text-blue-300'
                        : 'border-zinc-700 bg-zinc-800/50 text-zinc-400 hover:border-zinc-600 hover:text-zinc-300',
                      isComplete && 'border-green-500/50 bg-green-500/10 text-green-300',
                      isFailed && 'border-red-500/50 bg-red-500/10 text-red-300'
                    )}
                  >
                    <span>{info.label}</span>
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-[10px]',
                        isSelected && 'border-blue-500/30 text-blue-400',
                        isComplete && 'border-green-500/30 text-green-400',
                        isFailed && 'border-red-500/30 text-red-400'
                      )}
                    >
                      {info.aspectRatio}
                    </Badge>

                    {/* Status icon overlay */}
                    {isComplete && (
                      <CheckCircle2 className="absolute -top-1 -right-1 h-3.5 w-3.5 text-green-400" />
                    )}
                    {isFailed && (
                      <XCircle className="absolute -top-1 -right-1 h-3.5 w-3.5 text-red-400" />
                    )}
                  </button>
                )
              }
            )}
          </div>
        </div>

        {/* ===== Export button ===== */}
        <Button
          onClick={handleExport}
          disabled={selectedPlatforms.size === 0 || isExporting || hasActiveTasks}
          variant="default"
          size="default"
          className="w-full"
        >
          {isExporting || hasActiveTasks ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Exporting...</span>
            </>
          ) : allSelectedComplete ? (
            <>
              <CheckCircle2 className="h-4 w-4" />
              <span>All Exports Complete</span>
            </>
          ) : (
            <>
              <Monitor className="h-4 w-4" />
              <span>
                Export Selected ({selectedPlatforms.size}{' '}
                {selectedPlatforms.size === 1 ? 'platform' : 'platforms'})
              </span>
            </>
          )}
        </Button>

        {/* ===== Single-platform existing video ===== */}
        {hasVideo && videoUrl && selectedPlatforms.size === 0 && (
          <div className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
            <Video className="h-5 w-5 text-green-400 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-zinc-300">Current video ready</p>
              <p className="text-xs text-zinc-500 truncate">{videoUrl}</p>
            </div>
            <Button size="xs" variant="outline" className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 shrink-0">
              <a
                href={videoUrl}
                download
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1"
              >
                <Download className="h-3 w-3" />
                <span>Download</span>
              </a>
            </Button>
          </div>
        )}

        {/* ===== Per-platform progress ===== */}
        {Object.keys(platformTasks).length > 0 && (
          <div className="space-y-2">
            <span className="text-xs text-zinc-500 uppercase tracking-wider">
              Export Progress
            </span>

            <div className="space-y-2">
              {(Object.entries(platformTasks) as [Platform, PlatformTaskState | null][]).map(
                ([platform, task]) => {
                  if (!task) return null
                  const info = PLATFORM_INFO[platform]

                  return (
                    <div
                      key={platform}
                      className={cn(
                        'rounded-lg border p-3 transition-colors',
                        task.status === 'completed' && 'border-green-500/30 bg-green-500/5',
                        task.status === 'failed' && 'border-red-500/30 bg-red-500/5',
                        task.status === 'running' && 'border-blue-500/30 bg-blue-500/5',
                        task.status === 'pending' && 'border-zinc-700 bg-zinc-800/30'
                      )}
                    >
                      <div className="flex items-center justify-between mb-2">
                        {/* Platform label + status */}
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-zinc-200">
                            {info.label}
                          </span>
                          <Badge variant="outline" className="text-[10px] border-zinc-700 text-zinc-500">
                            {info.aspectRatio}
                          </Badge>
                        </div>

                        {/* Status badge */}
                        <div className="flex items-center gap-2">
                          {task.status === 'running' && (
                            <span className="text-xs text-blue-400 flex items-center gap-1">
                              <Loader2 className="h-3 w-3 animate-spin" />
                              {task.progress}%
                            </span>
                          )}
                          {task.status === 'completed' && (
                            <span className="text-xs text-green-400 flex items-center gap-1">
                              <CheckCircle2 className="h-3 w-3" />
                              Ready
                            </span>
                          )}
                          {task.status === 'failed' && (
                            <span className="text-xs text-red-400 flex items-center gap-1">
                              <XCircle className="h-3 w-3" />
                              Failed
                            </span>
                          )}
                          {task.status === 'pending' && (
                            <span className="text-xs text-zinc-500">Waiting...</span>
                          )}
                        </div>
                      </div>

                      {/* Progress bar */}
                      {(task.status === 'running' || task.status === 'pending') && (
                        <div className="h-1 rounded-full bg-zinc-800 overflow-hidden mb-1.5">
                          <div
                            className={cn(
                              'h-full rounded-full transition-all duration-500',
                              task.status === 'running' ? 'bg-blue-500' : 'bg-zinc-700'
                            )}
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                      )}

                      {/* Message or error */}
                      {task.message && task.status !== 'completed' && (
                        <p
                          className={cn(
                            'text-xs',
                            task.status === 'failed' ? 'text-red-400' : 'text-zinc-500'
                          )}
                        >
                          {task.status === 'failed' && task.error
                            ? task.error
                            : task.message}
                        </p>
                      )}

                      {/* Download button for completed */}
                      {task.status === 'completed' && task.videoUrl && (
                        <a
                          href={task.videoUrl}
                          download
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button
                            size="xs"
                            variant="outline"
                            className="mt-1 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                          >
                            <Download className="h-3 w-3" />
                            <span className="ml-1">Download {info.label} Video</span>
                          </Button>
                        </a>
                      )}
                    </div>
                  )
                }
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
