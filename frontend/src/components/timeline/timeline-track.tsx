'use client'

import { useRef, useCallback, useMemo } from 'react'
import { GripHorizontal } from 'lucide-react'
import { TimelineSegment } from './timeline-segment'
import { TransitionSelector } from './transition-selector'
import {
  useTimelineStore,
  getSegmentOffset,
  type TrackType,
  type TransitionType,
} from '@/stores/timeline-store'
import type { ScriptSegment } from '@/lib/api'
import { cn } from '@/lib/utils'

// ===== Props =====

interface TimelineTrackProps {
  label: string
  trackType: TrackType
  totalWidth: number
  pixelsPerSecond: number
}

// ===== Track label config =====

const TRACK_LABEL_CONFIG: Record<TrackType, { bg: string; text: string; border: string }> = {
  script: {
    bg: 'bg-zinc-900',
    text: 'text-zinc-300',
    border: 'border-zinc-800',
  },
  video: {
    bg: 'bg-zinc-900/70',
    text: 'text-zinc-400',
    border: 'border-zinc-800',
  },
  bgm: {
    bg: 'bg-zinc-900/50',
    text: 'text-zinc-500',
    border: 'border-zinc-800',
  },
  effects: {
    bg: 'bg-zinc-900/30',
    text: 'text-zinc-500',
    border: 'border-zinc-800',
  },
}

// ===== Component =====

export function TimelineTrack({
  label,
  trackType,
  totalWidth,
  pixelsPerSecond,
}: TimelineTrackProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const resizeStateRef = useRef<{
    index: number
    edge: 'left' | 'right'
    startX: number
  } | null>(null)

  const segments = useTimelineStore((s) => s.segments)
  const selectedIndex = useTimelineStore((s) => s.selectedIndex)
  const transitions = useTimelineStore((s) => s.transitions)
  const zoom = useTimelineStore((s) => s.zoom)
  const setSelectedIndex = useTimelineStore((s) => s.setSelectedIndex)
  const adjustBoundary = useTimelineStore((s) => s.adjustBoundary)
  const updateSegmentDuration = useTimelineStore((s) => s.updateSegmentDuration)
  const setTransition = useTimelineStore((s) => s.setTransition)

  const config = TRACK_LABEL_CONFIG[trackType]

  // Compute segment positions (sorted by index)
  const positioned = useMemo(() => {
    return segments.map((seg) => ({
      segment: seg,
      left: getSegmentOffset(segments, seg.index) * pixelsPerSecond,
      width: seg.estimated_duration_sec * pixelsPerSecond,
    }))
  }, [segments, pixelsPerSecond])

  // ---- Resize handling ----

  const handleResizeStart = useCallback(
    (index: number, edge: 'left' | 'right', e: React.MouseEvent) => {
      e.preventDefault()
      resizeStateRef.current = { index, edge, startX: e.clientX }

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const state = resizeStateRef.current
        if (!state) return

        const pixelDelta = moveEvent.clientX - state.startX
        const deltaSec = pixelDelta / pixelsPerSecond

        if (state.edge === 'left') {
          // Dragging left edge of state.index
          // Left edge of segment N = boundary between N-1 and N
          adjustBoundary(state.index, Math.round(deltaSec))
        } else {
          // Dragging right edge of state.index
          const idx = segments.findIndex((s) => s.index === state.index)
          const isLast = idx === segments.length - 1

          if (isLast) {
            // Last segment: freely change duration
            const seg = segments[idx]
            updateSegmentDuration(
              state.index,
              seg.estimated_duration_sec + Math.round(deltaSec)
            )
          } else {
            // Right edge of N = boundary between N and N+1
            const nextIndex = segments[idx + 1].index
            // Positive delta -> N gets longer, N+1 gets shorter
            adjustBoundary(nextIndex, Math.round(-deltaSec))
          }
        }

        // Update start position for relative deltas
        resizeStateRef.current = {
          ...state,
          startX: moveEvent.clientX,
        }
      }

      const handleMouseUp = () => {
        resizeStateRef.current = null
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }

      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    },
    [segments, pixelsPerSecond, adjustBoundary, updateSegmentDuration]
  )

  // ---- Context menu actions ----

  const handleContextMenuAction = useCallback(
    (action: 'replace' | 'delete' | 'split', index: number) => {
      switch (action) {
        case 'delete':
          // For now: remove the segment from the store
          useTimelineStore.setState((state) => ({
            segments: state.segments
              .filter((s) => s.index !== index)
              .map((s, i) => ({ ...s, index: i })),
            selectedIndex:
              state.selectedIndex === index ? null : state.selectedIndex,
          }))
          break
        case 'split': {
          // Split the segment into two halves
          const seg = segments.find((s) => s.index === index)
          if (!seg) return
          const halfDuration = Math.max(1, Math.floor(seg.estimated_duration_sec / 2))
          const newSegments = segments.flatMap((s) => {
            if (s.index !== index) return [s]
            return [
              { ...s, estimated_duration_sec: halfDuration },
              { ...s, index: s.index + 1, estimated_duration_sec: s.estimated_duration_sec - halfDuration },
            ]
          }).map((s, i) => ({ ...s, index: i }))
          useTimelineStore.setState({ segments: newSegments })
          break
        }
        case 'replace':
          // Toggle to a different segment type for demo
          useTimelineStore.setState((state) => ({
            segments: state.segments.map((s) => {
              if (s.index !== index) return s
              const types: ScriptSegment['type'][] = [
                'hook', 'intro', 'plot', 'twist', 'climax', 'ending',
              ]
              const currentIdx = types.indexOf(s.type)
              const nextType = types[(currentIdx + 1) % types.length]
              return { ...s, type: nextType }
            }),
          }))
          break
      }
    },
    [segments]
  )

  // ---- Transition handling ----

  const handleTransitionSelect = useCallback(
    (betweenIndex: number, type: TransitionType) => {
      setTransition(betweenIndex, type)
    },
    [setTransition]
  )

  const handleTransitionToggle = useCallback(
    (betweenIndex: number) => {
      const current = transitions[betweenIndex] || 'cut'
      const types: TransitionType[] = ['cut', 'dissolve', 'fade', 'slide', 'zoom']
      const idx = types.indexOf(current)
      const next = types[(idx + 1) % types.length]
      setTransition(betweenIndex, next)
    },
    [transitions, setTransition]
  )

  // ---- Track background click (deselect) ----

  const handleTrackClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === trackRef.current || (e.target as HTMLElement).dataset.trackBg) {
        setSelectedIndex(null)
      }
    },
    [setSelectedIndex]
  )

  return (
    <div
      className={cn(
        'flex border-b border-zinc-800',
        config.bg,
        trackType === 'script' && 'min-h-[52px]',
        trackType !== 'script' && 'min-h-[36px]'
      )}
    >
      {/* Track label (sticky left) */}
      <div
        className={cn(
          'sticky left-0 z-10 w-20 shrink-0 flex items-center gap-1 px-2',
          'border-r border-zinc-800',
          config.bg,
          config.text
        )}
      >
        <GripHorizontal className="h-3 w-3 opacity-40 shrink-0" />
        <span className="text-[11px] font-medium truncate">{label}</span>
      </div>

      {/* Segment area */}
      <div
        ref={trackRef}
        className="relative flex-1"
        style={{ width: totalWidth, minWidth: totalWidth }}
        data-track-bg="true"
        onClick={handleTrackClick}
      >
        {/* Transition indicators (only for video track) */}
        {trackType === 'video' &&
          positioned.slice(0, -1).map(({ segment, left, width }) => {
            const transitionPos = left + width
            const betweenIndex = positioned.find(
              (p) => p.segment.index === segment.index + 1
            )?.segment.index

            if (betweenIndex == null) return null

            return (
              <TransitionSelector
                key={`tr-${segment.index}`}
                position={transitionPos}
                currentType={transitions[betweenIndex] || 'cut'}
                isSelected={false}
                onSelect={(type) => handleTransitionSelect(betweenIndex, type)}
                onToggle={() => handleTransitionToggle(betweenIndex)}
              />
            )
          })}

        {/* Segments */}
        {positioned.map(({ segment, left, width }) => (
          <TimelineSegment
            key={`${trackType}-${segment.index}`}
            segment={segment}
            trackType={trackType}
            left={left}
            width={width}
            isSelected={selectedIndex === segment.index}
            isFirst={segment.index === 0}
            isLast={segment.index === segments.length - 1}
            pixelsPerSecond={pixelsPerSecond}
            onSelect={setSelectedIndex}
            onResizeStart={handleResizeStart}
            onContextMenuAction={handleContextMenuAction}
          />
        ))}
      </div>
    </div>
  )
}
