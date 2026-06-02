'use client'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

export const EMOTIONS = [
  { value: 'suspense', label: 'Suspense' },
  { value: 'buildup', label: 'Buildup' },
  { value: 'tense', label: 'Tense' },
  { value: 'revelation', label: 'Revelation' },
  { value: 'climax', label: 'Climax' },
  { value: 'reflection', label: 'Reflection' },
  { value: 'hope', label: 'Hope' },
  { value: 'comedy', label: 'Comedy' },
] as const

export type Emotion = (typeof EMOTIONS)[number]['value']

export const EMOTION_COLORS: Record<string, string> = {
  suspense: 'bg-red-900/50 text-red-300 border-red-800/50',
  buildup: 'bg-blue-900/50 text-blue-300 border-blue-800/50',
  tense: 'bg-purple-900/50 text-purple-300 border-purple-800/50',
  revelation: 'bg-yellow-900/50 text-yellow-300 border-yellow-800/50',
  climax: 'bg-red-900/50 text-red-300 border-red-800/50',
  reflection: 'bg-green-900/50 text-green-300 border-green-800/50',
  hope: 'bg-emerald-900/50 text-emerald-300 border-emerald-800/50',
  comedy: 'bg-amber-900/50 text-amber-300 border-amber-800/50',
}

interface EmotionSelectorProps {
  value: string
  onValueChange: (value: string) => void
  className?: string
}

export function EmotionSelector({ value, onValueChange, className }: EmotionSelectorProps) {
  const selectedEmotion = EMOTIONS.find((e) => e.value === value)

  const handleChange = (val: string | null) => {
    if (val) onValueChange(val)
  }

  return (
    <Select value={value} onValueChange={handleChange}>
      <SelectTrigger
        className={cn(
          'h-7 text-xs gap-1 min-w-[110px]',
          selectedEmotion
            ? EMOTION_COLORS[selectedEmotion.value]
            : 'border-zinc-700 bg-zinc-800/50 text-zinc-400',
          className
        )}
      >
        <SelectValue placeholder="Select emotion" />
      </SelectTrigger>
      <SelectContent className="bg-zinc-900 border-zinc-800">
        {EMOTIONS.map((emotion) => (
          <SelectItem
            key={emotion.value}
            value={emotion.value}
            className="text-xs text-zinc-300 focus:bg-zinc-800 focus:text-zinc-100"
          >
            <span
              className={cn(
                'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium',
                EMOTION_COLORS[emotion.value]
              )}
            >
              {emotion.label}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
