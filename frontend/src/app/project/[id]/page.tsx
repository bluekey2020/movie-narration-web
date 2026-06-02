'use client'

import { useEffect, useMemo, useCallback, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout/app-layout'
import { useProjectStore } from '@/stores/project-store'
import { useTaskStore } from '@/stores/task-store'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Loader2,
  FileText,
  Mic,
  Download,
  AlertCircle,
  Clock,
  Type,
  Hash,
  RefreshCw,
  History,
  GitCompare,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ScriptSegment, Platform } from '@/lib/api'
import { SegmentEditor } from '@/components/script/segment-editor'
import { EMOTION_COLORS } from '@/components/script/emotion-selector'
import { TimelineEditor } from '@/components/timeline/timeline-editor'
import { PlatformExportPanel } from '@/components/export/platform-export-panel'
import { ProgressStepper } from '@/components/generation/progress-stepper'
import { type AiAction } from '@/components/script/ai-toolbar'
import { estimateDuration } from '@/components/script/pause-marker'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { QualityRadarChart } from '@/components/script/quality-radar-chart'
import type { VariantKey } from '@/components/script/quality-radar-chart'
import { HookScoreGauge } from '@/components/script/hook-score-gauge'
import {
  VersionComparePanel,
  deriveVersionData,
} from '@/components/script/version-compare-panel'
import type { ScriptVersion } from '@/components/script/version-compare-panel'

// ===== 7-segment structure definition =====

const SEGMENT_SLOTS = [
  { id: 'hook', label: 'Hook', desc: 'Opening grab' },
  { id: 'intro', label: 'Intro', desc: 'Set the scene' },
  { id: 'plot1', label: 'Plot 1', desc: 'First arc' },
  { id: 'twist', label: 'Twist', desc: 'The turn' },
  { id: 'plot2', label: 'Plot 2', desc: 'Second arc' },
  { id: 'climax', label: 'Climax', desc: 'The peak' },
  { id: 'ending', label: 'Ending', desc: 'Wrap up' },
] as const

// Map data segment types to slot IDs
function mapSegmentsToSlots(segments: ScriptSegment[]) {
  const slotMap: Record<string, ScriptSegment | null> = {
    hook: null,
    intro: null,
    plot1: null,
    twist: null,
    plot2: null,
    climax: null,
    ending: null,
  }

  let plotIndex = 0
  for (const seg of segments) {
    if (seg.type === 'plot') {
      plotIndex++
      if (plotIndex === 1) slotMap.plot1 = seg
      else if (plotIndex === 2) slotMap.plot2 = seg
    } else if (slotMap.hasOwnProperty(seg.type)) {
      slotMap[seg.type] = seg
    }
  }

  return slotMap
}

const PLATFORM_OPTIONS: { value: Platform; label: string }[] = [
  { value: 'douyin', label: 'Douyin' },
  { value: 'bilibili', label: 'Bilibili' },
  { value: 'kuaishou', label: 'Kuaishou' },
  { value: 'xiaohongshu', label: 'Xiaohongshu' },
]

const STYLE_OPTIONS = [
  { value: 'suspense', label: 'Suspense Thriller' },
  { value: 'fast_paced', label: 'Fast-Paced' },
  { value: 'emotional', label: 'Emotional Drama' },
  { value: 'comedic', label: 'Comedic' },
  { value: 'analytical', label: 'Analytical' },
]

// ===== Component =====

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { currentProject, isLoading, fetchProject, updateProject } =
    useProjectStore()
  const { activeTask } = useTaskStore()

  const [selectedStyle, setSelectedStyle] = useState('')
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('douyin')
  const [aiLoadingSegments, setAiLoadingSegments] = useState<Set<number>>(new Set())
  const [compareOpen, setCompareOpen] = useState(false)
  const [selectedVariant, setSelectedVariant] = useState<VariantKey | null>(null)

  useEffect(() => {
    if (id) fetchProject(id)
  }, [id, fetchProject])

  useEffect(() => {
    if (currentProject) {
      setSelectedStyle(currentProject.style_id || '')
      setSelectedPlatform(currentProject.platform || 'douyin')
    }
  }, [currentProject])

  // Map script segments to 7 slots
  const slotMap = useMemo(
    () =>
      currentProject?.script_segments
        ? mapSegmentsToSlots(currentProject.script_segments)
        : {},
    [currentProject?.script_segments]
  )

  // Total script stats
  const totalStats = useMemo(() => {
    const allSegments = currentProject?.script_segments || []
    let totalWords = 0
    let totalDuration = 0
    for (const seg of allSegments) {
      const text = seg.text || ''
      totalWords += text.trim().split(/\s+/).filter(Boolean).length
      totalDuration += estimateDuration(text)
    }
    return { totalWords, totalDuration }
  }, [currentProject?.script_segments])

  // Derive 3 simulated script versions for comparison
  const versionData = useMemo(() => {
    const segments = currentProject?.script_segments || []
    if (segments.length === 0) return []
    return deriveVersionData(segments)
  }, [currentProject?.script_segments])

  // Scroll to segment
  const scrollToSegment = useCallback((slotId: string) => {
    const el = document.getElementById(`segment-${slotId}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [])

  // Handle segment text/emotion update (local only for now, could save to backend)
  const handleSegmentUpdate = useCallback(
    (updated: ScriptSegment) => {
      if (!currentProject) return
      const newSegments = currentProject.script_segments.map((s) =>
        s.index === updated.index ? updated : s
      )
      // We optimistically update via the store
      // updateProject would go to the backend; for now we work locally
      useProjectStore.setState({
        currentProject: { ...currentProject, script_segments: newSegments },
      })
    },
    [currentProject]
  )

  // Handle AI action on a segment
  const handleAiAction = useCallback(
    (action: AiAction, segment: ScriptSegment, emotion?: string) => {
      setAiLoadingSegments((prev) => new Set(prev).add(segment.index))

      // Placeholder: simulate AI processing
      // In production, this would call the generation API
      setTimeout(() => {
        setAiLoadingSegments((prev) => {
          const next = new Set(prev)
          next.delete(segment.index)
          return next
        })

        // Simulate a text change based on action
        let newText = segment.text
        switch (action) {
          case 'rewrite':
            newText = segment.text + '\n[AI rewrite placeholder]'
            break
          case 'shorten':
            newText = segment.text.split('.').slice(0, Math.ceil(segment.text.split('.').length / 2)).join('.') + '.'
            break
          case 'expand':
            newText = segment.text + ' [AI expansion placeholder — more detail would be generated here.]'
            break
          case 'change_emotion':
            if (emotion) {
              handleSegmentUpdate({ ...segment, emotion, text: segment.text + ` [AI regenerated with ${emotion} emotion]` })
              return
            }
            break
        }
        handleSegmentUpdate({ ...segment, text: newText })
      }, 1200)
    },
    [handleSegmentUpdate]
  )

  // Regenerate all script
  const handleRegenerateAll = useCallback(() => {
    // Placeholder
    alert('Regenerate All: This would regenerate all 7 segments with the selected style and platform.')
  }, [])

  // Handle version selection from compare dialog
  const handleCompareSelect = useCallback(
    (version: ScriptVersion) => {
      setSelectedVariant(version.key)
      // In production, this would apply the chosen variant's script to the project
      // For now we just track the selection visually
    },
    [],
  )

  // Loading state
  if (isLoading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
        </div>
      </AppLayout>
    )
  }

  // Not found state
  if (!currentProject) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <AlertCircle className="h-8 w-8 text-zinc-500" />
          <p className="text-sm text-zinc-400">Project not found</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push('/dashboard')}
          >
            Back to Dashboard
          </Button>
        </div>
      </AppLayout>
    )
  }

  // Check if script is available
  const hasScript = currentProject.script_segments.length > 0

  return (
    <AppLayout title={currentProject.movie_title}>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* ===== Generation progress stepper ===== */}
        {activeTask && activeTask.project_id === id && (
          <Card className="border-zinc-800 bg-zinc-900">
            <CardContent className="p-5">
              <ProgressStepper
                onRetry={(stage) => {
                  // TODO: Wire up actual retry logic via generation API
                  console.warn(`Retry requested for stage: ${stage}`)
                }}
              />
            </CardContent>
          </Card>
        )}

        {/* ===== Workbench tabs ===== */}
        <Tabs defaultValue="script" className="w-full">
          <TabsList className="bg-zinc-900 border border-zinc-800">
            <TabsTrigger value="script" className="gap-2">
              <FileText className="h-4 w-4" />
              Script
            </TabsTrigger>
            <TabsTrigger value="voice" className="gap-2">
              <Mic className="h-4 w-4" />
              Voice
            </TabsTrigger>
            <TabsTrigger value="timeline" className="gap-2">
              <Clock className="h-4 w-4" />
              Timeline
            </TabsTrigger>
            <TabsTrigger value="export" className="gap-2">
              <Download className="h-4 w-4" />
              Export
            </TabsTrigger>
          </TabsList>

          {/* ===== Script Tab ===== */}
          <TabsContent value="script" className="mt-4">
            {!hasScript ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-500">
                <FileText className="h-10 w-10" />
                <p className="text-sm">
                  {activeTask
                    ? 'Script is being generated...'
                    : 'Script generation has not started yet'}
                </p>
              </div>
            ) : (
              <div className="flex gap-6">
                {/* ===== 7-Segment Navigation Sidebar ===== */}
                <nav className="shrink-0 w-48">
                  <div className="sticky top-6 space-y-0.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600 mb-3 px-2">
                      Segments
                    </p>
                    {SEGMENT_SLOTS.map((slot) => {
                      const seg = slotMap[slot.id]
                      const isActive = !!seg
                      const emotionColor = seg
                        ? EMOTION_COLORS[seg.emotion] || 'bg-zinc-800'
                        : ''

                      return (
                        <button
                          key={slot.id}
                          onClick={() => scrollToSegment(slot.id)}
                          className={cn(
                            'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors group',
                            isActive
                              ? 'text-zinc-300 hover:bg-zinc-800/50'
                              : 'text-zinc-600 cursor-not-allowed'
                          )}
                          disabled={!isActive}
                        >
                          {/* Active indicator dot */}
                          <span
                            className={cn(
                              'shrink-0 h-2 w-2 rounded-full transition-colors',
                              isActive
                                ? 'bg-blue-500'
                                : 'bg-zinc-700'
                            )}
                          />
                          <span className="text-xs font-medium flex-1">
                            {slot.label}
                          </span>
                          {seg && (
                            <span
                              className={cn(
                                'shrink-0 h-1.5 w-1.5 rounded-full',
                                emotionColor.split(' ').find((c) => c.startsWith('bg-')) || 'bg-zinc-600'
                              )}
                              title={seg.emotion}
                            />
                          )}
                        </button>
                      )
                    })}
                  </div>
                </nav>

                {/* ===== Main Editor Area ===== */}
                <div className="flex-1 min-w-0 space-y-4">
                  {/* Script-level toolbar */}
                  <div className="flex items-center gap-3 p-3 rounded-lg border border-zinc-800 bg-zinc-900/50">
                    {/* Style selector */}
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-zinc-600 uppercase tracking-wider">
                        Style
                      </span>
                      <Select
                        value={selectedStyle}
                        onValueChange={(v) => { if (v) setSelectedStyle(v) }}
                      >
                        <SelectTrigger className="h-7 text-xs border-zinc-700 bg-zinc-800/50 text-zinc-300 min-w-[140px]">
                          <SelectValue placeholder="Select style" />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-900 border-zinc-800">
                          {STYLE_OPTIONS.map((opt) => (
                            <SelectItem
                              key={opt.value}
                              value={opt.value}
                              className="text-xs text-zinc-300 focus:bg-zinc-800 focus:text-zinc-100"
                            >
                              {opt.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Platform selector */}
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-zinc-600 uppercase tracking-wider">
                        Platform
                      </span>
                      <Select
                        value={selectedPlatform}
                        onValueChange={(v) => { if (v) setSelectedPlatform(v as Platform) }}
                      >
                        <SelectTrigger className="h-7 text-xs border-zinc-700 bg-zinc-800/50 text-zinc-300 min-w-[120px]">
                          <SelectValue placeholder="Platform" />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-900 border-zinc-800">
                          {PLATFORM_OPTIONS.map((opt) => (
                            <SelectItem
                              key={opt.value}
                              value={opt.value}
                              className="text-xs text-zinc-300 focus:bg-zinc-800 focus:text-zinc-100"
                            >
                              {opt.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Divider */}
                    <div className="h-5 w-px bg-zinc-800" />

                    {/* Word count / Duration */}
                    <div className="flex items-center gap-3 text-xs text-zinc-500">
                      <span className="flex items-center gap-1">
                        <Type className="h-3 w-3" />
                        {totalStats.totalWords} words
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        ~{Math.round(totalStats.totalDuration)}s
                      </span>
                      <span className="flex items-center gap-1">
                        <Hash className="h-3 w-3" />
                        {currentProject.script_segments.length} segs
                      </span>
                    </div>

                    {/* Actions */}
                    <div className="ml-auto flex items-center gap-2">
                      {/* Version History dropdown */}
                      <DropdownMenu>
                        <DropdownMenuTrigger>
                          <Button
                            variant="ghost"
                            size="xs"
                            className="h-7 text-xs text-zinc-500 hover:text-zinc-300"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <History className="h-3 w-3" />
                            <span className="ml-1">History</span>
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          className="bg-zinc-900 border-zinc-800 w-48"
                          align="end"
                        >
                          <DropdownMenuItem
                            className="text-xs text-zinc-500 cursor-not-allowed"
                            disabled
                          >
                            No previous versions
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-xs text-zinc-500 cursor-not-allowed"
                            disabled
                          >
                            Version history coming soon
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>

                      {/* Compare versions */}
                      <Button
                        size="xs"
                        variant="outline"
                        className="h-7 text-xs border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                        onClick={() => setCompareOpen(true)}
                      >
                        <GitCompare className="h-3 w-3" />
                        <span className="ml-1">Compare</span>
                      </Button>

                      {/* Regenerate All */}
                      <Button
                        size="xs"
                        variant="outline"
                        className="h-7 text-xs border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                        onClick={handleRegenerateAll}
                      >
                        <RefreshCw className="h-3 w-3" />
                        <span className="ml-1">Regenerate All</span>
                      </Button>
                    </div>
                  </div>

                  {/* Segment Editors */}
                  <div className="space-y-3">
                    {SEGMENT_SLOTS.map((slot) => {
                      const seg = slotMap[slot.id]
                      if (!seg) return null

                      return (
                        <SegmentEditor
                          key={slot.id}
                          segment={seg}
                          displayType={seg.type === 'plot' ? slot.id : seg.type}
                          onUpdate={handleSegmentUpdate}
                          onAiAction={handleAiAction}
                          isAiLoading={aiLoadingSegments.has(seg.index)}
                        />
                      )
                    })}
                  </div>
                </div>
              </div>
            )}
          </TabsContent>

          {/* ===== Voice Tab ===== */}
          <TabsContent value="voice" className="mt-4">
            <Card className="border-zinc-800 bg-zinc-900">
              <CardContent className="p-6 text-center">
                <Mic className="h-10 w-10 text-zinc-500 mx-auto mb-3" />
                <p className="text-sm text-zinc-400">
                  Voice generation controls will appear here
                </p>
                <p className="text-xs text-zinc-600 mt-1">
                  Once the script is ready, you can select voice characters and
                  adjust parameters
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ===== Timeline Tab ===== */}
          <TabsContent value="timeline" className="mt-4">
            {!hasScript ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-500">
                <Clock className="h-10 w-10" />
                <p className="text-sm">
                  {activeTask
                    ? 'Timeline will be available once the script is generated...'
                    : 'Generate a script first to see the timeline'}
                </p>
              </div>
            ) : (
              <TimelineEditor
                segments={currentProject.script_segments}
              />
            )}
          </TabsContent>

          {/* ===== Export Tab ===== */}
          <TabsContent value="export" className="mt-4">
            <PlatformExportPanel
              projectId={currentProject.project_id}
              movieId={currentProject.movie_id}
              style={currentProject.style_id}
              voiceId={currentProject.voice_id}
              hasVideo={!!currentProject.output_url}
              videoUrl={currentProject.output_url}
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* ===== Version Compare Dialog ===== */}
      <Dialog open={compareOpen} onOpenChange={setCompareOpen}>
        <DialogContent
          className="max-w-[1100px] bg-zinc-950 border-zinc-800 text-zinc-200"
          showCloseButton
        >
          <DialogHeader>
            <DialogTitle className="text-zinc-100">
              Script Version Comparison
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Compare 3 AI-generated script variants and choose the best one for
              your narration.
            </DialogDescription>
          </DialogHeader>

          {versionData.length > 0 && (() => {
            const bestVersion =
              versionData.reduce((best, v) =>
                v.qualityScore > best.qualityScore ? v : best,
              )
            const displayVersion =
              versionData.find((v) => v.key === selectedVariant) || bestVersion

            return (
              <div className="space-y-6 mt-2">
                {/* Top row: Radar chart + Hook gauge */}
                <div className="flex items-start gap-8 justify-center">
                  <QualityRadarChart variants={versionData} />
                  {displayVersion && (
                    <HookScoreGauge
                      score={displayVersion.hookScore}
                      hookType={displayVersion.hookType}
                      suggestions={displayVersion.hookSuggestions}
                    />
                  )}
                </div>

                {/* Three-column comparison panel */}
                <VersionComparePanel
                  versions={versionData}
                  selectedKey={selectedVariant}
                  onSelect={handleCompareSelect}
                />
              </div>
            )
          })()}
        </DialogContent>
      </Dialog>
    </AppLayout>
  )
}
