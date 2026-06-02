'use client'

import { useEffect, useMemo, useRef, useCallback } from 'react'
import { ZoomIn, ZoomOut, Clock, Play, Pause, SkipBack, SkipForward } from 'lucide-react'
import { TimelineRuler } from './timeline-ruler'
import { TimelineTrack } from './timeline-track'
import {
  useTimelineStore,
  getPixelsPerSecond,
  getTotalDuration,
  ZOOM_LEVELS,
  type ZoomLevel,
} from '@/stores/timeline-store'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ScriptSegment } from '@/lib/api'

// ===== Props =====

interface TimelineEditorProps {
  segments: ScriptSegment[]
  className?: string
}

// ===== Component =====

export function TimelineEditor({ segments, className }: TimelineEditorProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const cursorRef = useRef<HTMLDivElement>(null)

  const storeSegments = useTimelineStore((s) => s.segments)
  const zoom = useTimelineStore((s) => s.zoom)
  const currentTime = useTimelineStore((s) => s.currentTime)
  const isPlaying = useTimelineStore((s) => s.isPlaying)
  const setSegments = useTimelineStore((s) => s.setSegments)
  const setZoom = useTimelineStore((s) => s.setZoom)
  const zoomIn = useTimelineStore((s) => s.zoomIn)
  const zoomOut = useTimelineStore((s) => s.zoomOut)
  const setCurrentTime = useTimelineStore((s) => s.setCurrentTime)
  const setSelectedIndex = useTimelineStore((s) => s.setSelectedIndex)

  // Load segments into the store on mount / when segments prop changes
  useEffect(() => {
    setSegments(segments)
  }, [segments, setSegments])

  // Derived values
  const pps = useMemo(() => getPixelsPerSecond(zoom), [zoom])
  const totalDuration = useMemo(
    () => getTotalDuration(storeSegments),
    [storeSegments]
  )
  const totalWidth = useMemo(() => {
    return Math.max(totalDuration * pps, 800)
  }, [totalDuration, pps])

  // ---- Keyboard shortcuts ----

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Space to toggle play/pause
      if (e.code === 'Space' && e.target === document.body) {
        e.preventDefault()
        useTimelineStore.setState((s) => ({ isPlaying: !s.isPlaying }))
      }

      // +/- for zoom
      if (e.code === 'Equal' || e.code === 'NumpadAdd') {
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault()
          zoomIn()
        }
      }
      if (e.code === 'Minus' || e.code === 'NumpadSubtract') {
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault()
          zoomOut()
        }
      }

      // Left/Right arrows for seeking
      if (e.code === 'ArrowLeft') {
        e.preventDefault()
        const state = useTimelineStore.getState()
        state.setCurrentTime(Math.max(0, state.currentTime - 1))
      }
      if (e.code === 'ArrowRight') {
        e.preventDefault()
        const state = useTimelineStore.getState()
        state.setCurrentTime(
          Math.min(state.currentTime + 1, getTotalDuration(state.segments))
        )
      }

      // Escape to deselect
      if (e.code === 'Escape') {
        setSelectedIndex(null)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [zoomIn, zoomOut, setSelectedIndex])

  // ---- Playback simulation ----

  useEffect(() => {
    if (!isPlaying) return

    const interval = setInterval(() => {
      const state = useTimelineStore.getState()
      const nextTime = state.currentTime + 0.1
      const total = getTotalDuration(state.segments)

      if (nextTime >= total) {
        state.setCurrentTime(0)
        state.isPlaying = false
      } else {
        state.setCurrentTime(nextTime)
      }
    }, 100)

    return () => clearInterval(interval)
  }, [isPlaying])

  // ---- Auto-scroll to follow cursor during playback ----

  useEffect(() => {
    if (!isPlaying || !scrollRef.current) return
    const cursorX = currentTime * pps
    const container = scrollRef.current
    const viewLeft = container.scrollLeft
    const viewRight = viewLeft + container.clientWidth

    // If cursor is about to go off-screen, scroll to follow
    if (cursorX > viewRight - 200) {
      container.scrollLeft = cursorX - 200
    }
  }, [currentTime, pps, isPlaying])

  // ---- Zoom with Ctrl+Scroll ----

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault()
        if (e.deltaY < 0) {
          zoomIn()
        } else {
          zoomOut()
        }
      }
    },
    [zoomIn, zoomOut]
  )

  // ---- Click on ruler to seek ----

  const handleRulerClick = useCallback(
    (e: React.MouseEvent) => {
      const rulerEl = e.currentTarget as HTMLElement
      const rect = rulerEl.getBoundingClientRect()
      const x = e.clientX - rect.left + (scrollRef.current?.scrollLeft || 0)
      const time = Math.max(0, Math.min(x / pps, totalDuration))
      setCurrentTime(Math.round(time))
    },
    [pps, totalDuration, setCurrentTime]
  )

  // ===== Empty state =====

  if (storeSegments.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-16 gap-3 text-zinc-500', className)}>
        <Clock className="h-10 w-10" />
        <p className="text-sm">No segments to display</p>
        <p className="text-xs text-zinc-600">
          Generate a script first to see the timeline
        </p>
      </div>
    )
  }

  // ===== Main render =====

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* ===== Toolbar ===== */}
      <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900/50">
        {/* Playback controls */}
        <div className="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon-xs"
            className="text-zinc-400 hover:text-zinc-200"
            onClick={() => setCurrentTime(0)}
            title="Go to start"
          >
            <SkipBack className="h-3 w-3" />
          </Button>

          <Button
            variant="ghost"
            size="icon-xs"
            className="text-zinc-400 hover:text-zinc-200"
            onClick={() =>
              useTimelineStore.setState((s) => ({ isPlaying: !s.isPlaying }))
            }
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="h-3.5 w-3.5" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
          </Button>

          <Button
            variant="ghost"
            size="icon-xs"
            className="text-zinc-400 hover:text-zinc-200"
            onClick={() => {
              const state = useTimelineStore.getState()
              state.setCurrentTime(getTotalDuration(state.segments))
            }}
            title="Go to end"
          >
            <SkipForward className="h-3 w-3" />
          </Button>
        </div>

        {/* Time display */}
        <div className="flex items-center gap-1 text-xs text-zinc-400 font-mono">
          <span>
            {Math.floor(currentTime / 60)}:
            {Math.floor(currentTime % 60)
              .toString()
              .padStart(2, '0')}
          </span>
          <span className="text-zinc-600">/</span>
          <span>
            {Math.floor(totalDuration / 60)}:
            {Math.floor(totalDuration % 60)
              .toString()
              .padStart(2, '0')}
          </span>
        </div>

        {/* Divider */}
        <div className="h-5 w-px bg-zinc-800" />

        {/* Zoom controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-xs"
            className="text-zinc-400 hover:text-zinc-200"
            onClick={zoomOut}
            disabled={zoom <= ZOOM_LEVELS[0]}
            title="Zoom out"
          >
            <ZoomOut className="h-3 w-3" />
          </Button>

          <span className="text-xs text-zinc-400 font-mono min-w-[36px] text-center select-none">
            {zoom}x
          </span>

          <Button
            variant="ghost"
            size="icon-xs"
            className="text-zinc-400 hover:text-zinc-200"
            onClick={zoomIn}
            disabled={zoom >= ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
            title="Zoom in"
          >
            <ZoomIn className="h-3 w-3" />
          </Button>
        </div>

        {/* Keyboard hints */}
        <div className="ml-auto flex items-center gap-3 text-[10px] text-zinc-600">
          <span>Ctrl+Scroll to zoom</span>
          <span>Space to play</span>
          <span>&larr;&rarr; to seek</span>
        </div>
      </div>

      {/* ===== Timeline ===== */}
      <div
        ref={scrollRef}
        className="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-950 relative"
        onWheel={handleWheel}
      >
        <div style={{ minWidth: totalWidth }}>
          {/* Ruler */}
          <div className="flex">
            {/* Ruler label placeholder (aligns with track labels) */}
            <div className="sticky left-0 z-10 w-20 shrink-0 border-r border-b border-zinc-800 bg-zinc-900" />

            {/* Ruler */}
            <div
              className="flex-1 cursor-pointer"
              style={{ width: totalWidth, minWidth: totalWidth }}
              onClick={handleRulerClick}
            >
              <TimelineRuler
                totalDurationSec={totalDuration}
                pixelsPerSecond={pps}
              />
            </div>
          </div>

          {/* Tracks */}
          <TimelineTrack
            label="Script"
            trackType="script"
            totalWidth={totalWidth}
            pixelsPerSecond={pps}
          />
          <TimelineTrack
            label="Video"
            trackType="video"
            totalWidth={totalWidth}
            pixelsPerSecond={pps}
          />
          <TimelineTrack
            label="BGM"
            trackType="bgm"
            totalWidth={totalWidth}
            pixelsPerSecond={pps}
          />
          <TimelineTrack
            label="Effects"
            trackType="effects"
            totalWidth={totalWidth}
            pixelsPerSecond={pps}
          />

          {/* ===== Time cursor (red vertical line) ===== */}
          <div
            ref={cursorRef}
            className="absolute top-0 bottom-0 z-30 pointer-events-none"
            style={{ left: 80 + currentTime * pps }}
          >
            {/* Cursor head (triangle) */}
            <div className="relative">
              <div
                className="absolute -top-1"
                style={{
                  width: 0,
                  height: 0,
                  borderLeft: '6px solid transparent',
                  borderRight: '6px solid transparent',
                  borderTop: '8px solid #ef4444',
                }}
              />
            </div>
            {/* Cursor line */}
            <div className="w-0.5 h-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
          </div>
        </div>
      </div>
    </div>
  )
}
