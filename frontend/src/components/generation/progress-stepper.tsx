'use client'

import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, Loader2, Clock, XCircle, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TaskStage, TaskProgress } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

// ===== Stage configuration =====

const STAGES: { key: TaskStage; label: string }[] = [
  { key: 'script_generation', label: 'Script Generation' },
  { key: 'scene_matching', label: 'Scene Matching' },
  { key: 'voice_generation', label: 'Voice Generation' },
  { key: 'bgm_planning', label: 'BGM Planning' },
  { key: 'video_composition', label: 'Video Composition' },
]

type StageState = 'waiting' | 'running' | 'completed' | 'failed'

interface StageInfo {
  key: TaskStage
  label: string
  state: StageState
  progress?: number
  message?: string
  error?: string
}

interface StageTiming {
  startedAt: number
  endedAt?: number
}

// ===== Helpers =====

function deriveStages(activeTask: TaskProgress | null): StageInfo[] {
  const currentIndex = activeTask
    ? STAGES.findIndex((s) => s.key === activeTask.stage)
    : -1

  const allDone = activeTask?.stage === 'done'

  return STAGES.map((stage, i) => {
    const info: StageInfo = {
      key: stage.key,
      label: stage.label,
      state: 'waiting',
    }

    if (allDone || (currentIndex >= 0 && i < currentIndex)) {
      info.state = 'completed'
    } else if (i === currentIndex) {
      if (activeTask!.status === 'failed') {
        info.state = 'failed'
        info.error = activeTask!.error
      } else {
        info.state = 'running'
        info.progress = activeTask!.progress
        info.message = activeTask!.message
      }
    }

    return info
  })
}

function formatElapsed(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000))
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

// ===== ProgressStepper Component =====

interface ProgressStepperProps {
  onRetry?: (stage: TaskStage) => void
  className?: string
}

export function ProgressStepper({ onRetry, className }: ProgressStepperProps) {
  const { activeTask } = useTaskStore()
  const stages = deriveStages(activeTask)

  // Track stage start/end timestamps locally
  const stageTimings = useRef<Record<string, StageTiming>>({})
  const [, forceRender] = useState(0)
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Detect stage state transitions and record timestamps
  useEffect(() => {
    const now = Date.now()
    for (const stage of stages) {
      const timing = stageTimings.current[stage.key]

      if (stage.state === 'running') {
        if (!timing) {
          stageTimings.current[stage.key] = { startedAt: now }
        } else if (!timing.startedAt) {
          timing.startedAt = now
        }
      }

      if (
        (stage.state === 'completed' || stage.state === 'failed') &&
        timing &&
        !timing.endedAt
      ) {
        timing.endedAt = now
      }
    }
  }, [stages])

  // Tick once per second to refresh elapsed time display while running
  const hasRunning = stages.some((s) => s.state === 'running')

  useEffect(() => {
    if (hasRunning) {
      tickRef.current = setInterval(() => forceRender((n) => n + 1), 1000)
    }
    return () => {
      if (tickRef.current) {
        clearInterval(tickRef.current)
        tickRef.current = null
      }
    }
  }, [hasRunning])

  // Reset timings when there's no task
  useEffect(() => {
    if (!activeTask) {
      stageTimings.current = {}
    }
  }, [activeTask])

  if (!activeTask) return null

  return (
    <div className={cn('space-y-0', className)}>
      {stages.map((stage, i) => (
        <StageRow
          key={stage.key}
          stage={stage}
          isLast={i === stages.length - 1}
          timing={stageTimings.current[stage.key]}
          onRetry={() => onRetry?.(stage.key)}
        />
      ))}
    </div>
  )
}

// ===== StageRow (internal sub-component) =====

interface StageRowProps {
  stage: StageInfo
  isLast: boolean
  timing?: StageTiming
  onRetry: () => void
}

function StageRow({ stage, isLast, timing, onRetry }: StageRowProps) {
  const { state, label, progress, message, error } = stage

  // Compute elapsed time for the stage
  let elapsedStr: string | null = null
  if (timing) {
    if (timing.endedAt) {
      elapsedStr = formatElapsed(timing.endedAt - timing.startedAt)
    } else {
      elapsedStr = formatElapsed(Date.now() - timing.startedAt)
    }
  }

  return (
    <div className="flex">
      {/* ===== Icon column with connector line ===== */}
      <div className="flex flex-col items-center mr-4">
        <StageIcon state={state} />
        {!isLast && <ConnectorLine state={state} />}
      </div>

      {/* ===== Content column ===== */}
      <div
        className={cn(
          'flex-1 pb-5',
          state === 'waiting' && 'opacity-40'
        )}
      >
        {/* Top row: label + badge + time/progress */}
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={cn(
              'text-sm font-medium',
              state === 'waiting' && 'text-zinc-500',
              state === 'running' && 'text-blue-400',
              state === 'completed' && 'text-green-400',
              state === 'failed' && 'text-red-400'
            )}
          >
            {label}
          </span>

          <StatusBadge state={state} />

          {state === 'running' && progress !== undefined && (
            <span className="text-xs text-zinc-500 ml-auto">
              {progress}%
            </span>
          )}

          {state === 'completed' && elapsedStr && (
            <span className="text-xs text-zinc-500 ml-auto">
              {elapsedStr}
            </span>
          )}
        </div>

        {/* ===== Running: progress bar + message ===== */}
        {state === 'running' && (
          <div className="mt-1.5">
            <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-blue-500 transition-all duration-500"
                style={{ width: `${progress ?? 0}%` }}
              />
            </div>
            {message && (
              <p className="mt-1 text-xs text-zinc-500">{message}</p>
            )}
          </div>
        )}

        {/* ===== Failed: error + retry ===== */}
        {state === 'failed' && (
          <div className="mt-1.5 space-y-1.5">
            {error && (
              <p className="text-xs text-red-400">{error}</p>
            )}
            <Button
              variant="outline"
              size="xs"
              className="h-6 gap-1 text-xs border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
              onClick={onRetry}
            >
              <RefreshCw className="h-3 w-3" />
              Retry
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

// ===== StageIcon =====

interface StageIconProps {
  state: StageState
}

function StageIcon({ state }: StageIconProps) {
  const baseClasses =
    'shrink-0 flex items-center justify-center h-8 w-8 rounded-full border-2 transition-colors'

  switch (state) {
    case 'completed':
      return (
        <div className={cn(baseClasses, 'border-green-500 bg-green-500/10')}>
          <CheckCircle2 className="h-4 w-4 text-green-500" />
        </div>
      )
    case 'running':
      return (
        <div className={cn(baseClasses, 'border-blue-500 bg-blue-500/10')}>
          <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />
        </div>
      )
    case 'failed':
      return (
        <div className={cn(baseClasses, 'border-red-500 bg-red-500/10')}>
          <XCircle className="h-4 w-4 text-red-500" />
        </div>
      )
    case 'waiting':
    default:
      return (
        <div className={cn(baseClasses, 'border-zinc-700 bg-zinc-900')}>
          <Clock className="h-4 w-4 text-zinc-600" />
        </div>
      )
  }
}

// ===== ConnectorLine =====

interface ConnectorLineProps {
  state: StageState
}

function ConnectorLine({ state }: ConnectorLineProps) {
  return (
    <div
      className={cn(
        'w-0.5 flex-1 min-h-6 my-0.5 rounded-full',
        state === 'completed' && 'bg-green-500/40',
        state === 'running' && 'bg-blue-500/30',
        state === 'failed' && 'bg-red-500/40',
        state === 'waiting' && 'bg-zinc-800'
      )}
    />
  )
}

// ===== StatusBadge =====

interface StatusBadgeProps {
  state: StageState
}

function StatusBadge({ state }: StatusBadgeProps) {
  const variantConfig: Record<
    StageState,
    { label: string; className: string }
  > = {
    completed: {
      label: 'Completed',
      className: 'bg-green-500/10 text-green-400 border-green-500/20',
    },
    running: {
      label: 'Running',
      className: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    },
    waiting: {
      label: 'Waiting',
      className: 'bg-zinc-800 text-zinc-500 border-zinc-700',
    },
    failed: {
      label: 'Failed',
      className: 'bg-red-500/10 text-red-400 border-red-500/20',
    },
  }

  const config = variantConfig[state]

  return (
    <Badge
      variant="outline"
      className={cn('text-[10px] px-1.5 py-0', config.className)}
    >
      {config.label}
    </Badge>
  )
}
