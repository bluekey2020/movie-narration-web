'use client'

import { useMemo } from 'react'
import { cn } from '@/lib/utils'

interface TimelineRulerProps {
  totalDurationSec: number
  pixelsPerSecond: number
  className?: string
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export function TimelineRuler({
  totalDurationSec,
  pixelsPerSecond,
  className,
}: TimelineRulerProps) {
  const ticks = useMemo(() => {
    const result: { position: number; label: string | null; isMajor: boolean }[] = []

    // Determine tick interval based on zoom
    const interval = pixelsPerSecond > 80 ? 10 : pixelsPerSecond > 40 ? 15 : 30

    for (let t = 0; t <= totalDurationSec; t += interval) {
      result.push({
        position: t * pixelsPerSecond,
        label: t % 30 === 0 ? formatTime(t) : null,
        isMajor: t % 30 === 0,
      })
    }

    // Ensure the end marker is always present
    const lastTick = result[result.length - 1]
    if (lastTick && lastTick.position < totalDurationSec * pixelsPerSecond - 2) {
      result.push({
        position: totalDurationSec * pixelsPerSecond,
        label: formatTime(totalDurationSec),
        isMajor: true,
      })
    }

    return result
  }, [totalDurationSec, pixelsPerSecond])

  return (
    <div
      className={cn(
        'relative h-8 border-b border-zinc-800 bg-zinc-900/80 select-none',
        className
      )}
    >
      {ticks.map((tick, i) => (
        <div
          key={i}
          className="absolute top-0 flex flex-col items-center"
          style={{ left: tick.position }}
        >
          {/* Tick mark */}
          <div
            className={cn(
              'w-px',
              tick.isMajor ? 'h-4 bg-zinc-500' : 'h-2 bg-zinc-700'
            )}
          />
          {/* Label */}
          {tick.label && (
            <span className="mt-0.5 text-[10px] leading-none text-zinc-500 whitespace-nowrap">
              {tick.label}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
