'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { ScriptSegment } from '@/lib/api'
import { EmotionSelector } from './emotion-selector'
import { AiToolbar, type AiAction } from './ai-toolbar'
import { PauseMarkers, estimateDuration } from './pause-marker'
import { Clock, Type } from 'lucide-react'

const SEGMENT_NAMES: Record<string, string> = {
  hook: 'Hook',
  intro: 'Intro',
  plot: 'Plot',
  twist: 'Twist',
  climax: 'Climax',
  ending: 'Ending',
}

interface SegmentEditorProps {
  segment: ScriptSegment
  displayType: string
  onUpdate: (updated: ScriptSegment) => void
  onAiAction: (action: AiAction, segment: ScriptSegment, emotion?: string) => void
  isAiLoading?: boolean
  className?: string
}

/**
 * Build a map of word positions in the text for emphasis toggling.
 * Returns an array of { word, startIndex, endIndex } for each word in the text.
 */
function buildWordMap(text: string): Array<{ word: string; startIndex: number; endIndex: number }> {
  const words: Array<{ word: string; startIndex: number; endIndex: number }> = []
  const regex = /[\p{L}\p{N}]+/gu
  let match: RegExpExecArray | null
  while ((match = regex.exec(text)) !== null) {
    words.push({
      word: match[0],
      startIndex: match.index,
      endIndex: match.index + match[0].length,
    })
  }
  return words
}

export function SegmentEditor({
  segment,
  displayType,
  onUpdate,
  onAiAction,
  isAiLoading = false,
  className,
}: SegmentEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [localText, setLocalText] = useState(segment.text)
  const [wordMap, setWordMap] = useState<ReturnType<typeof buildWordMap>>([])
  const duration = estimateDuration(localText)
  const wordCount = localText.trim().split(/\s+/).filter(Boolean).length

  useEffect(() => {
    setLocalText(segment.text)
  }, [segment.text])

  useEffect(() => {
    setWordMap(buildWordMap(localText))
  }, [localText])

  // Auto-grow textarea
  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${el.scrollHeight}px`
    }
  }, [localText, isEditing])

  const handleTextChange = useCallback((value: string) => {
    setLocalText(value)
  }, [])

  const handleTextBlur = useCallback(() => {
    setIsEditing(false)
    if (localText !== segment.text) {
      onUpdate({ ...segment, text: localText })
    }
  }, [localText, segment, onUpdate])

  const handleEmotionChange = useCallback(
    (value: string) => {
      onUpdate({ ...segment, emotion: value })
    },
    [segment, onUpdate]
  )

  // Toggle emphasis word
  const handleWordClick = useCallback(
    (word: string) => {
      const current = segment.emphasis_words || []
      let updated: string[]
      if (current.includes(word)) {
        updated = current.filter((w) => w !== word)
      } else {
        updated = [...current, word]
      }
      onUpdate({ ...segment, emphasis_words: updated })
    },
    [segment, onUpdate]
  )

  const handleAiAction = useCallback(
    (action: AiAction, emotion?: string) => {
      onAiAction(action, segment, emotion)
    },
    [segment, onAiAction]
  )

  const displayName = SEGMENT_NAMES[displayType] || displayType

  return (
    <Card
      id={`segment-${segment.index}`}
      className={cn('border-zinc-800 bg-zinc-900/80 backdrop-blur transition-all group', className)}
    >
      <CardContent className="p-4 space-y-3">
        {/* Header row */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-wider">
            {displayName}
          </span>
          <span className="text-[10px] font-mono text-zinc-700">
            Seg {segment.index}
          </span>
          <EmotionSelector
            value={segment.emotion}
            onValueChange={handleEmotionChange}
          />
          {/* Duration / word count */}
          <div className="ml-auto flex items-center gap-3 text-[10px] text-zinc-600">
            <span className="flex items-center gap-1">
              <Type className="h-3 w-3" />
              {wordCount} words
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              ~{duration}s
            </span>
          </div>
        </div>

        {/* Text editing area */}
        <div className="relative">
          {isEditing ? (
            <textarea
              ref={textareaRef}
              value={localText}
              onChange={(e) => handleTextChange(e.target.value)}
              onBlur={handleTextBlur}
              className="w-full min-h-[80px] resize-none bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 leading-relaxed focus:outline-none focus:border-zinc-600 focus:ring-1 focus:ring-zinc-600 transition-colors"
              placeholder="Write your narration text here... Use <#0.5#> for pause markers."
              autoFocus
            />
          ) : (
            <div
              className="cursor-text min-h-[60px] rounded-lg px-3 py-2 text-sm text-zinc-300 leading-relaxed hover:bg-zinc-800/30 transition-colors border border-transparent hover:border-zinc-800"
              onClick={() => setIsEditing(true)}
            >
              {localText ? (
                <PauseMarkers text={localText} />
              ) : (
                <span className="text-zinc-600 italic">
                  Click to edit narration text...
                </span>
              )}
            </div>
          )}
        </div>

        {/* Emphasis words display */}
        {(segment.emphasis_words?.length || 0) > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] text-zinc-600 mr-1">Emphasis:</span>
            {segment.emphasis_words!.map((word) => {
              const isInText = wordMap.some((w) => w.word === word)
              return (
                <Badge
                  key={word}
                  variant="outline"
                  className={cn(
                    'text-[10px] cursor-pointer transition-colors',
                    isInText
                      ? 'border-amber-700/50 text-amber-400 hover:bg-amber-900/30'
                      : 'border-zinc-700 text-zinc-500 line-through hover:bg-zinc-800/50'
                  )}
                >
                  <span
                    className="cursor-pointer"
                    onClick={() => handleWordClick(word)}
                    title={isInText ? 'Click to remove emphasis' : 'Word not in current text'}
                  >
                    {word}
                  </span>
                </Badge>
              )
            })}
          </div>
        )}

        {/* In-editing word highlighting info */}
        {isEditing && wordMap.length > 0 && (
          <div className="text-[10px] text-zinc-600">
            Click words in the text to toggle emphasis. Emphasized words are{' '}
            <span className="text-amber-400 font-semibold">highlighted</span> in the preview.
            Use <code className="text-zinc-500 bg-zinc-800 px-1 rounded">{'<#0.5#>'}</code> for pause markers.
          </div>
        )}

        {/* AI Toolbar */}
        <div className="pt-1 border-t border-zinc-800/50">
          <AiToolbar
            onAction={handleAiAction}
            isLoading={isAiLoading}
            className="justify-end"
          />
        </div>
      </CardContent>
    </Card>
  )
}
