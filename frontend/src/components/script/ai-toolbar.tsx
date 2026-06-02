'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Wand2,
  Shrink,
  Expand,
  Smile,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { EMOTIONS } from './emotion-selector'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export type AiAction = 'rewrite' | 'shorten' | 'expand' | 'change_emotion'

interface AiToolbarProps {
  onAction: (action: AiAction, emotion?: string) => void
  isLoading?: boolean
  className?: string
}

const ACTIONS: Array<{
  id: AiAction
  label: string
  icon: typeof Wand2
  needsEmotion?: boolean
}> = [
  { id: 'rewrite', label: 'Rewrite', icon: Wand2 },
  { id: 'shorten', label: 'Shorten', icon: Shrink },
  { id: 'expand', label: 'Expand', icon: Expand },
  { id: 'change_emotion', label: 'Change Emotion', icon: Smile, needsEmotion: true },
]

export function AiToolbar({ onAction, isLoading, className }: AiToolbarProps) {
  const [activeAction, setActiveAction] = useState<AiAction | null>(null)
  const [emotionMenuOpen, setEmotionMenuOpen] = useState(false)

  const handleAction = (action: AiAction) => {
    if (action === 'change_emotion') {
      setEmotionMenuOpen(true)
      return
    }
    setActiveAction(action)
    onAction(action)
  }

  const handleEmotionSelect = (emotion: string) => {
    setEmotionMenuOpen(false)
    setActiveAction('change_emotion')
    onAction('change_emotion', emotion)
  }

  return (
    <div className={cn('flex items-center gap-1', className)}>
      {ACTIONS.map((action) => {
        const isActive = activeAction === action.id && isLoading
        const Icon = action.icon

        if (action.needsEmotion) {
          return (
            <DropdownMenu
              key={action.id}
              open={emotionMenuOpen}
              onOpenChange={setEmotionMenuOpen}
            >
              <DropdownMenuTrigger>
                <Button
                  variant="ghost"
                  size="xs"
                  className="h-7 text-xs text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
                  disabled={isLoading}
                  onClick={(e) => {
                    e.stopPropagation()
                  }}
                >
                  {isActive ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Icon className="h-3 w-3" />
                  )}
                  <span className="ml-1">{action.label}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="bg-zinc-900 border-zinc-800 w-36"
                align="start"
              >
                {EMOTIONS.map((emotion) => (
                  <DropdownMenuItem
                    key={emotion.value}
                    className="text-xs text-zinc-300 cursor-pointer focus:bg-zinc-800 focus:text-zinc-100"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleEmotionSelect(emotion.value)
                    }}
                  >
                    {emotion.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )
        }

        return (
          <Button
            key={action.id}
            variant="ghost"
            size="xs"
            className="h-7 text-xs text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
            disabled={isLoading}
            onClick={(e) => {
              e.stopPropagation()
              handleAction(action.id)
            }}
          >
            {isActive ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Icon className="h-3 w-3" />
            )}
            <span className="ml-1">{action.label}</span>
          </Button>
        )
      })}
    </div>
  )
}
