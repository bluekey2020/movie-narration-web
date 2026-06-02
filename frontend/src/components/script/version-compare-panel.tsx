'use client'

import { useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { PauseMarkers, estimateDuration } from './pause-marker'
import { Clock, Type, Star, Check } from 'lucide-react'
import type { ScriptSegment } from '@/lib/api'
import type { VariantKey } from './quality-radar-chart'
import type { QualityDimensions } from './quality-radar-chart'
import type { HookType } from './hook-score-gauge'

// ===== Types =====

export interface ScriptVersion {
  key: VariantKey
  name: string
  icon: string
  scriptText: string
  wordCount: number
  estimatedDuration: number
  qualityScore: number
  dimensions: QualityDimensions
  hookScore: number
  hookType: HookType
  hookSuggestions: string
  emotionTags: string[] // Inline emotion labels for each segment
}

// ===== Mock data generator =====

const VARIANT_NAMES: Record<VariantKey, { name: string; icon: string }> = {
  aggressive: { name: 'Aggressive', icon: '激进型' },        // 激进型
  stable: { name: 'Stable', icon: '稳健型' },               // 稳健型
  creative: { name: 'Creative', icon: '创意型' },           // 创意型
}

const VARIANT_EMOTIONS: Record<VariantKey, string[]> = {
  aggressive: ['suspense', 'tense', 'tense', 'climax', 'tense', 'climax', 'revelation'],
  stable: ['buildup', 'buildup', 'buildup', 'revelation', 'buildup', 'climax', 'reflection'],
  creative: ['comedy', 'hope', 'revelation', 'revelation', 'hope', 'revelation', 'reflection'],
}

const VARIANT_HOOK_TYPES: Record<VariantKey, HookType> = {
  aggressive: 'shock_value',
  stable: 'information_gap',
  creative: 'mystery_setup',
}

const VARIANT_HOOK_SUGGESTIONS: Record<VariantKey, string> = {
  aggressive:
    'The opening hook is strong but too abrupt. Consider adding a 0.5s pause before the first sentence to let the audience brace for impact.',
  stable:
    'Solid information gap technique. To boost engagement, try leading with a provocative question instead of a statement.',
  creative:
    'The mystery setup works well. Add a concrete visual reference in the first 3 seconds to ground the abstract opening.',
}

/**
 * Build a simulated script version by slightly modifying the original text
 * based on the variant's style. In production, these would come from the
 * AI generation backend as actual alternative outputs.
 */
function buildVariant(
  key: VariantKey,
  segments: ScriptSegment[],
): ScriptVersion {
  const emotions = VARIANT_EMOTIONS[key]
  const combined = segments
    .map((seg, i) => {
      const emotionTag = emotions[i % emotions.length]
      const text = tweakText(seg.text, key, i)
      return `<[${emotionTag}]> ${text}`
    })
    .join('\n\n')

  const wordCount = combined
    .replace(/<\[[^\]]+\]>/g, '')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length

  const duration = Math.round(estimateDuration(combined))

  // Slightly randomized quality metrics per variant
  const seed = key === 'aggressive' ? 1 : key === 'stable' ? 2 : 3
  const r = (base: number, variance: number) =>
    Math.round(Math.max(60, Math.min(98, base + variance * seed)))

  const dimensions: QualityDimensions = {
    hookAppeal: key === 'aggressive' ? r(88, 3) : key === 'stable' ? r(72, 2) : r(80, -1),
    informationDensity: key === 'aggressive' ? r(92, -2) : key === 'stable' ? r(68, 3) : r(75, 4),
    rhythmCurve: key === 'aggressive' ? r(78, -1) : key === 'stable' ? r(85, 2) : r(90, -2),
    conversationalLevel: key === 'aggressive' ? r(65, 2) : key === 'stable' ? r(82, 1) : r(76, -3),
    durationCompliance: key === 'aggressive' ? r(70, 3) : key === 'stable' ? r(88, -1) : r(74, 2),
    styleConsistency: key === 'aggressive' ? r(75, 1) : key === 'stable' ? r(90, -2) : r(68, 3),
  }

  const qualityScore = Math.round(
    Object.values(dimensions).reduce((a, b) => a + b, 0) / 6,
  )

  return {
    key,
    name: VARIANT_NAMES[key].name,
    icon: VARIANT_NAMES[key].icon,
    scriptText: combined,
    wordCount,
    estimatedDuration: duration,
    qualityScore,
    dimensions,
    hookScore: key === 'aggressive' ? 76 : key === 'stable' ? 68 : 82,
    hookType: VARIANT_HOOK_TYPES[key],
    hookSuggestions: VARIANT_HOOK_SUGGESTIONS[key],
    emotionTags: emotions,
  }
}

/**
 * Slightly modify text to simulate different AI generations.
 * Each variant has a distinct personality in the output.
 */
function tweakText(text: string, variant: VariantKey, segmentIndex: number): string {
  if (!text || text.trim().length === 0) {
    return `[Segment ${segmentIndex + 1} placeholder for ${variant} variant]`
  }

  switch (variant) {
    case 'aggressive':
      // Add intensity — shorter sentences, more dramatic phrasing
      return text
        .replace(/。\s*/g, '！')  // periods → exclamations
        .replace(/\.\s*/g, '! ')

    case 'stable':
      // Keep mostly as-is with slight polish
      return text

    case 'creative':
      // Add metaphorical language hints
      return text
        .replace(/(是) (一)/g, '$1简直是 $2')  // 是 → 简直是
        .replace(/\b(is|was) (a)\b/gi, '$1 absolutely $2')

    default:
      return text
  }
}

// ===== Props =====

interface VersionComparePanelProps {
  versions: ScriptVersion[]
  selectedKey?: VariantKey | null
  onSelect: (version: ScriptVersion) => void
  className?: string
}

// ===== Score color helper =====

function scoreBadgeColor(score: number): string {
  if (score >= 85) return 'bg-green-900/50 text-green-300 border-green-700/50'
  if (score >= 70) return 'bg-yellow-900/50 text-yellow-300 border-yellow-700/50'
  return 'bg-red-900/50 text-red-300 border-red-700/50'
}

// ===== Component =====

/**
 * Side-by-side comparison of 3 AI-generated script variants.
 * Each column shows: variant name, stats, full script text with emotion tags,
 * and a Select button. The highest-scoring variant gets a green border.
 */
export function VersionComparePanel({
  versions,
  selectedKey,
  onSelect,
  className,
}: VersionComparePanelProps) {
  const bestKey = useMemo(() => {
    if (versions.length === 0) return null
    return versions.reduce((best, v) =>
      v.qualityScore > best.qualityScore ? v : best,
    ).key
  }, [versions])

  if (versions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-2 text-zinc-500">
        <p className="text-sm">No version data available</p>
        <p className="text-xs">Generate a script first to see version comparisons</p>
      </div>
    )
  }

  return (
    <div className={cn('', className)}>
      <div className="grid grid-cols-3 gap-4">
        {versions.map((version) => {
          const isBest = version.key === bestKey
          const isSelected = version.key === selectedKey

          return (
            <Card
              key={version.key}
              className={cn(
                'border transition-colors',
                isBest
                  ? 'border-green-500/50 bg-green-950/10'
                  : 'border-zinc-800 bg-zinc-900/50',
                isSelected && 'ring-1 ring-blue-500/50',
              )}
            >
              <CardContent className="p-4 space-y-3">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-zinc-200">
                      {version.name}
                    </span>
                    <span className="text-xs text-zinc-600">{version.icon}</span>
                    {isBest && (
                      <Badge className="bg-green-900/50 text-green-300 border-green-700/50 text-[10px]">
                        <Star className="h-2.5 w-2.5 mr-0.5" />
                        Best
                      </Badge>
                    )}
                    {isSelected && (
                      <Badge className="bg-blue-900/50 text-blue-300 border-blue-700/50 text-[10px]">
                        <Check className="h-2.5 w-2.5 mr-0.5" />
                        Active
                      </Badge>
                    )}
                  </div>
                  <Badge
                    variant="outline"
                    className={cn('text-[10px]', scoreBadgeColor(version.qualityScore))}
                  >
                    {version.qualityScore}
                  </Badge>
                </div>

                {/* Stats row */}
                <div className="flex items-center gap-3 text-[10px] text-zinc-500">
                  <span className="flex items-center gap-1">
                    <Type className="h-2.5 w-2.5" />
                    {version.wordCount} words
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-2.5 w-2.5" />
                    ~{version.estimatedDuration}s
                  </span>
                </div>

                {/* Emotion tag chips */}
                <div className="flex flex-wrap gap-1">
                  {Array.from(new Set(version.emotionTags)).map((tag) => (
                    <Badge
                      key={tag}
                      variant="outline"
                      className="text-[9px] border-zinc-700 text-zinc-500"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>

                {/* Script text */}
                <div className="max-h-[320px] overflow-y-auto rounded-lg bg-zinc-950/60 border border-zinc-800/50 p-3">
                  <div className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">
                    <PauseMarkers text={version.scriptText} />
                  </div>
                </div>

                {/* Emotion tag legend inline */}
                <div className="text-[10px] text-zinc-600 space-y-0.5">
                  <p>
                    Emotion tags shown inline as{' '}
                    <code className="text-zinc-500 bg-zinc-800 px-1 rounded text-[9px]">
                      {'<[emotion]>'}
                    </code>{' '}
                    prefixes.
                  </p>
                </div>

                {/* Select button */}
                <Button
                  size="sm"
                  variant={isSelected ? 'secondary' : 'outline'}
                  className={cn(
                    'w-full h-8 text-xs',
                    isSelected
                      ? 'bg-blue-900/30 border-blue-700/50 text-blue-300'
                      : 'border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800',
                  )}
                  onClick={() => onSelect(version)}
                  disabled={isSelected}
                >
                  {isSelected ? (
                    <>
                      <Check className="h-3 w-3" />
                      Selected
                    </>
                  ) : (
                    'Select'
                  )}
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

// ===== Derived data hook =====

/**
 * Builds 3 simulated script versions from the current project's segments.
 * In production, replace with real AI-generated version data from the backend.
 */
export function deriveVersionData(
  segments: ScriptSegment[],
): ScriptVersion[] {
  return (['aggressive', 'stable', 'creative'] as VariantKey[]).map((key) =>
    buildVariant(key, segments),
  )
}
