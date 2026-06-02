'use client'

import { cn } from '@/lib/utils'

const PAUSE_REGEX = /<#(\d+(?:\.\d+)?)#>/g

interface PauseMarkerProps {
  text: string
  className?: string
}

interface ParsedPause {
  /** Duration in seconds, parsed from the marker */
  durationSec: number
  /** The original marker text like "<#0.5#>" */
  raw: string
}

/**
 * Renders text with <#0.5#> pause markers as colored inline badges.
 * Each marker shows the duration in seconds as a small badge.
 */
export function PauseMarkers({ text, className }: PauseMarkerProps) {
  const parts: Array<{ type: 'text' | 'pause'; value: string; durationSec?: number }> = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  const regex = new RegExp(PAUSE_REGEX.source, 'g')
  while ((match = regex.exec(text)) !== null) {
    // Push text before this marker
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, match.index) })
    }
    const durationSec = parseFloat(match[1])
    parts.push({ type: 'pause', value: match[0], durationSec })
    lastIndex = match.index + match[0].length
  }

  // Push remaining text
  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) })
  }

  if (parts.length === 0) {
    return <span className={cn('text-zinc-300', className)}>{text}</span>
  }

  return (
    <span className={cn('inline', className)}>
      {parts.map((part, i) => {
        if (part.type === 'pause') {
          return (
            <span
              key={i}
              className="inline-flex items-center mx-0.5 px-1 py-px rounded text-[10px] font-mono font-medium bg-amber-900/50 text-amber-300 border border-amber-700/50 align-middle cursor-default select-none"
              title={`Pause ${part.durationSec}s`}
            >
              {part.durationSec!.toFixed(1)}s
            </span>
          )
        }
        return <span key={i}>{part.value}</span>
      })}
    </span>
  )
}

/**
 * Extract all pause markers from text.
 */
export function parsePauseMarkers(text: string): ParsedPause[] {
  const results: ParsedPause[] = []
  const regex = new RegExp(PAUSE_REGEX.source, 'g')
  let match: RegExpExecArray | null
  while ((match = regex.exec(text)) !== null) {
    results.push({
      durationSec: parseFloat(match[1]),
      raw: match[0],
    })
  }
  return results
}

/**
 * Insert a pause marker at a given position in the text.
 */
export function insertPauseMarker(text: string, position: number, durationSec: number): string {
  const marker = `<#${durationSec}#>`
  return text.slice(0, position) + marker + text.slice(position)
}

/**
 * Remove a pause marker by its raw text.
 */
export function removePauseMarker(text: string, markerRaw: string): string {
  return text.replace(markerRaw, '')
}

/**
 * Calculate estimated reading time accounting for pause markers.
 * Returns total seconds including pauses.
 */
export function estimateDuration(text: string, wordsPerSec = 2.8): number {
  // Remove pause markers for word counting
  const cleanText = text.replace(PAUSE_REGEX, '')
  const wordCount = cleanText.trim().split(/\s+/).filter(Boolean).length
  const readingSec = wordCount / wordsPerSec

  // Add up pause durations
  const pauses = parsePauseMarkers(text)
  const pauseTotal = pauses.reduce((sum, p) => sum + p.durationSec, 0)

  return Math.round((readingSec + pauseTotal) * 10) / 10
}

/**
 * Strip pause markers from text for clean display or editing.
 */
export function stripPauseMarkers(text: string): string {
  return text.replace(PAUSE_REGEX, '')
}
