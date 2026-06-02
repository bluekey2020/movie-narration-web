'use client'

import { useState, useCallback, useEffect } from 'react'
import { Scissors, ArrowRight, Layers, MoveRight, ZoomIn } from 'lucide-react'
import {
  type TransitionType,
  TRANSITION_CONFIG,
} from '@/stores/timeline-store'
import { cn } from '@/lib/utils'

// ===== Props =====

interface TransitionSelectorProps {
  /** Center position between two segments (in pixels) */
  position: number
  currentType: TransitionType
  isSelected: boolean
  onSelect: (type: TransitionType) => void
  onToggle: () => void
}

// ===== Transition type to icon mapping =====

const TRANSITION_ICONS: Record<TransitionType, React.ReactNode> = {
  cut: <Scissors className="h-3 w-3" />,
  dissolve: <Layers className="h-3 w-3" />,
  fade: <ArrowRight className="h-3 w-3" />,
  slide: <MoveRight className="h-3 w-3" />,
  zoom: <ZoomIn className="h-3 w-3" />,
}

const ALL_TRANSITIONS: TransitionType[] = [
  'cut',
  'dissolve',
  'fade',
  'slide',
  'zoom',
]

// ===== Component =====

export function TransitionSelector({
  position,
  currentType,
  isSelected,
  onSelect,
  onToggle,
}: TransitionSelectorProps) {
  const [isHovered, setIsHovered] = useState(false)
  const [showMenu, setShowMenu] = useState(false)

  // Close menu on outside click
  useEffect(() => {
    if (!showMenu) return
    const handler = () => setShowMenu(false)
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [showMenu])

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onToggle()
    },
    [onToggle]
  )

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      setShowMenu((prev) => !prev)
    },
    []
  )

  const handleSelect = useCallback(
    (type: TransitionType, e: React.MouseEvent) => {
      e.stopPropagation()
      onSelect(type)
      setShowMenu(false)
    },
    [onSelect]
  )

  return (
    <div
      className="absolute top-0 bottom-0 z-20 flex items-center justify-center"
      style={{ left: position }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => {
        setIsHovered(false)
        setShowMenu(false)
      }}
    >
      {/* Transition indicator */}
      <button
        className={cn(
          'relative flex items-center justify-center',
          'w-5 h-5 rounded-full border transition-all duration-150',
          isHovered || showMenu
            ? 'border-blue-400 bg-blue-500/20 scale-125'
            : 'border-zinc-600 bg-zinc-800',
          isSelected && 'border-blue-500 bg-blue-500/30'
        )}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        title={`${TRANSITION_CONFIG[currentType].label} (double-click to change)`}
      >
        <span
          className={cn(
            'text-[8px]',
            isHovered || showMenu ? 'text-blue-300' : 'text-zinc-500'
          )}
        >
          {TRANSITION_ICONS[currentType]}
        </span>
      </button>

      {/* Transition type label on hover */}
      {(isHovered || showMenu) && (
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <span className="text-[10px] text-blue-300 bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-700">
            {TRANSITION_CONFIG[currentType].label}
          </span>
        </div>
      )}

      {/* Transition type picker menu */}
      {showMenu && (
        <div className="absolute top-8 left-1/2 -translate-x-1/2 z-50 min-w-[120px] rounded-lg border border-zinc-700 bg-zinc-800 shadow-xl py-1">
          {ALL_TRANSITIONS.map((type) => (
            <button
              key={type}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-1.5 text-xs transition-colors',
                type === currentType
                  ? 'text-blue-300 bg-blue-500/10'
                  : 'text-zinc-300 hover:bg-zinc-700'
              )}
              onClick={(e) => handleSelect(type, e)}
            >
              <span className="text-zinc-400">{TRANSITION_ICONS[type]}</span>
              <span>{TRANSITION_CONFIG[type].label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
