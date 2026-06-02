'use client'

import { useRef, useCallback, useState, useEffect } from 'react'
import {
  SEGMENT_COLORS,
  SEGMENT_BORDER_COLORS,
  SEGMENT_LABELS,
  SEGMENT_TO_EFFECT,
  EMOTION_TO_BGM,
  type SegmentType,
  type TrackType,
} from '@/stores/timeline-store'
import { cn } from '@/lib/utils'
import type { ScriptSegment } from '@/lib/api'

// ===== Props =====

interface TimelineSegmentProps {
  segment: ScriptSegment
  trackType: TrackType
  /** Left position in pixels */
  left: number
  /** Width in pixels */
  width: number
  /** Total pixel width of this segment on all tracks (same timing) */
  isSelected: boolean
  isFirst: boolean
  isLast: boolean
  pixelsPerSecond: number
  onSelect: (index: number) => void
  onResizeStart: (
    index: number,
    edge: 'left' | 'right',
    e: React.MouseEvent
  ) => void
  onContextMenuAction: (action: 'replace' | 'delete' | 'split', index: number) => void
}

// ===== Label derivation per track type =====

function getTrackLabel(segment: ScriptSegment, trackType: TrackType): string {
  switch (trackType) {
    case 'script':
      return segment.text
    case 'video':
      return (
        segment.visual_requirement.scene_hint ||
        segment.visual_requirement.description ||
        'Clip'
      )
    case 'bgm':
      return EMOTION_TO_BGM[segment.emotion] || segment.emotion || 'Neutral'
    case 'effects':
      return SEGMENT_TO_EFFECT[segment.type] || 'Cut'
    default:
      return ''
  }
}

function getTrackSecondaryLabel(
  segment: ScriptSegment,
  trackType: TrackType
): string {
  switch (trackType) {
    case 'script':
      return SEGMENT_LABELS[segment.type] || segment.type
    case 'video':
      return `Scene: ${segment.visual_requirement.mood || 'Neutral'}`
    case 'bgm':
      return segment.emotion || ''
    case 'effects':
      return segment.visual_requirement.mood || ''
    default:
      return ''
  }
}

// ===== Minimum segment width =====

const MIN_SEGMENT_WIDTH = 16

// ===== Component =====

export function TimelineSegment({
  segment,
  trackType,
  left,
  width,
  isSelected,
  isFirst,
  isLast,
  pixelsPerSecond,
  onSelect,
  onResizeStart,
  onContextMenuAction,
}: TimelineSegmentProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null)
  const color = SEGMENT_COLORS[segment.type] || 'bg-zinc-700'
  const borderColor = SEGMENT_BORDER_COLORS[segment.type] || 'border-zinc-500'
  const label = getTrackLabel(segment, trackType)
  const secondaryLabel = getTrackSecondaryLabel(segment, trackType)
  const displayWidth = Math.max(width, MIN_SEGMENT_WIDTH)

  // Close context menu on outside click
  useEffect(() => {
    if (!contextMenu) return
    const handleClick = () => setContextMenu(null)
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [contextMenu])

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onSelect(segment.index)
    },
    [segment.index, onSelect]
  )

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({ x: e.clientX, y: e.clientY })
  }, [])

  const handleLeftResize = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      e.preventDefault()
      // Left edge of first segment cannot be resized
      if (!isFirst) {
        onResizeStart(segment.index, 'left', e)
      }
    },
    [segment.index, isFirst, onResizeStart]
  )

  const handleRightResize = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      e.preventDefault()
      onResizeStart(segment.index, 'right', e)
    },
    [segment.index, onResizeStart]
  )

  const handleMenuAction = useCallback(
    (action: 'replace' | 'delete' | 'split') => {
      setContextMenu(null)
      onContextMenuAction(action, segment.index)
    },
    [segment.index, onContextMenuAction]
  )

  return (
    <>
      <div
        ref={ref}
        className={cn(
          'absolute top-0.5 bottom-0.5 rounded-md cursor-pointer select-none',
          'flex flex-col justify-center overflow-hidden',
          'transition-shadow duration-100',
          color,
          isSelected && `ring-2 ring-white/70 ${borderColor}`,
          !isSelected && 'hover:brightness-110'
        )}
        style={{
          left,
          width: displayWidth,
        }}
        onClick={handleClick}
        onContextMenu={handleContextMenu}
        title={`${SEGMENT_LABELS[segment.type]}: ${label}\nDuration: ${segment.estimated_duration_sec}s`}
      >
        {/* Content */}
        <div className="px-1.5 truncate">
          {trackType === 'script' ? (
            <>
              <div className="text-[10px] text-white/90 truncate leading-tight">
                {label}
              </div>
              <div className="text-[9px] text-white/50 truncate leading-tight">
                {secondaryLabel} &middot; {segment.estimated_duration_sec}s
              </div>
            </>
          ) : (
            <div className="flex flex-col justify-center h-full px-0.5">
              <span className="text-[10px] text-white/90 truncate leading-tight font-medium">
                {label}
              </span>
            </div>
          )}
        </div>

        {/* Left resize handle */}
        <div
          className={cn(
            'absolute left-0 top-0 bottom-0 w-2 cursor-col-resize',
            'hover:bg-white/20 group/handle',
            isFirst && 'hidden'
          )}
          onMouseDown={handleLeftResize}
        >
          <div className="absolute left-0.5 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded bg-white/0 group-hover/handle:bg-white/40 transition-colors" />
        </div>

        {/* Right resize handle */}
        <div
          className={cn(
            'absolute right-0 top-0 bottom-0 w-2 cursor-col-resize',
            'hover:bg-white/20 group/handle-r'
          )}
          onMouseDown={handleRightResize}
        >
          <div className="absolute right-0.5 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded bg-white/0 group-hover/handle-r:bg-white/40 transition-colors" />
        </div>
      </div>

      {/* Context menu */}
      {contextMenu && (
        <div
          className="fixed z-50 min-w-[140px] rounded-lg border border-zinc-700 bg-zinc-800 shadow-xl py-1"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-700 transition-colors"
            onClick={() => handleMenuAction('replace')}
          >
            Replace
          </button>
          <button
            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-700 transition-colors"
            onClick={() => handleMenuAction('split')}
          >
            Split
          </button>
          <div className="h-px bg-zinc-700 my-1" />
          <button
            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-400 hover:bg-zinc-700 transition-colors"
            onClick={() => handleMenuAction('delete')}
          >
            Delete
          </button>
        </div>
      )}
    </>
  )
}
