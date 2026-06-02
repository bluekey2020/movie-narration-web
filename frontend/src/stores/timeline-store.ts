import { create } from 'zustand'
import type { ScriptSegment, Project } from '@/lib/api'

// ===== Types =====

export type TransitionType = 'cut' | 'dissolve' | 'fade' | 'slide' | 'zoom'

export type SegmentType = ScriptSegment['type']

export const ZOOM_LEVELS = [0.5, 1, 2, 4] as const

export type ZoomLevel = (typeof ZOOM_LEVELS)[number]

/** Base pixels-per-second at zoom 1x */
export const PPS_BASE = 40

// ===== Segment color/display mapping =====

export const SEGMENT_COLORS: Record<SegmentType, string> = {
  hook: 'bg-red-600/80',
  intro: 'bg-blue-600/80',
  plot: 'bg-emerald-600/80',
  twist: 'bg-purple-600/80',
  climax: 'bg-orange-500/80',
  ending: 'bg-teal-600/80',
}

export const SEGMENT_BORDER_COLORS: Record<SegmentType, string> = {
  hook: 'border-red-400',
  intro: 'border-blue-400',
  plot: 'border-emerald-400',
  twist: 'border-purple-400',
  climax: 'border-orange-300',
  ending: 'border-teal-400',
}

export const SEGMENT_LABELS: Record<SegmentType, string> = {
  hook: 'Opening Hook',
  intro: 'Intro',
  plot: 'Plot',
  twist: 'Twist',
  climax: 'Climax',
  ending: 'Ending',
}

// ===== Track types =====

export type TrackType = 'script' | 'video' | 'bgm' | 'effects'

export interface TrackSegment {
  index: number
  label: string
  durationSec: number
  segmentType: SegmentType
}

// ===== Transition display info =====

export const TRANSITION_CONFIG: Record<TransitionType, { label: string; icon: string }> = {
  cut: { label: 'Cut', icon: 'Cut' },
  dissolve: { label: 'Dissolve', icon: 'Dissolve' },
  fade: { label: 'Fade', icon: 'Fade' },
  slide: { label: 'Slide', icon: 'Slide' },
  zoom: { label: 'Zoom', icon: 'Zoom' },
}

// ===== Emotion to BGM mapping =====

export const EMOTION_TO_BGM: Record<string, string> = {
  '紧张': 'Tense',
  '悬疑': 'Suspense',
  '激昂': 'Epic',
  '平静': 'Calm',
  '悲伤': 'Melancholic',
  '愉快': 'Upbeat',
  '兴奋': 'Energetic',
  '温馨': 'Warm',
  '恐怖': 'Horror',
  '感动': 'Moving',
  '热血': 'Passionate',
  '神秘': 'Mysterious',
}

// ===== Segment type to default effect mapping =====

export const SEGMENT_TO_EFFECT: Record<SegmentType, string> = {
  hook: 'Zoom In',
  intro: 'Fade In',
  plot: 'Shake',
  twist: 'Flash White',
  climax: 'Fast Cut',
  ending: 'Fade Out',
}

// ===== Store state =====

interface TimelineState {
  // Data
  segments: ScriptSegment[]

  // Playback
  currentTime: number
  isPlaying: boolean

  // Zoom
  zoom: ZoomLevel

  // Selection
  selectedIndex: number | null

  // Transitions between video segments
  // Key = the index of the right segment (the boundary after segment N is keyed by N+1)
  transitions: Record<number, TransitionType>

  // Actions
  setSegments: (segments: ScriptSegment[]) => void
  loadFromProject: (project: Project) => void
  setCurrentTime: (time: number) => void
  setZoom: (zoom: ZoomLevel) => void
  zoomIn: () => void
  zoomOut: () => void
  setSelectedIndex: (index: number | null) => void
  setTransition: (betweenIndex: number, type: TransitionType) => void
  updateSegmentDuration: (index: number, newDuration: number) => void
  adjustBoundary: (betweenIndex: number, deltaSec: number) => void
  reorderSegments: (fromIndex: number, toIndex: number) => void
}

// ===== Helpers =====

export function getPixelsPerSecond(zoom: ZoomLevel): number {
  return PPS_BASE * zoom
}

export function getTotalDuration(segments: ScriptSegment[]): number {
  return segments.reduce((sum, s) => sum + s.estimated_duration_sec, 0)
}

export function getSegmentOffset(
  segments: ScriptSegment[],
  targetIndex: number
): number {
  let offset = 0
  for (const seg of segments) {
    if (seg.index === targetIndex) break
    offset += seg.estimated_duration_sec
  }
  return offset
}

// ===== Store =====

export const useTimelineStore = create<TimelineState>((set, get) => ({
  segments: [],
  currentTime: 0,
  isPlaying: false,
  zoom: 1,
  selectedIndex: null,
  transitions: {},

  setSegments: (segments) => set({ segments }),

  loadFromProject: (project) => {
    set({
      segments: project.script_segments || [],
      currentTime: 0,
      selectedIndex: null,
      transitions: {},
    })
  },

  setCurrentTime: (currentTime) => set({ currentTime }),

  setZoom: (zoom) => set({ zoom }),

  zoomIn: () => {
    const current = get().zoom
    const idx = ZOOM_LEVELS.indexOf(current)
    if (idx < ZOOM_LEVELS.length - 1) {
      set({ zoom: ZOOM_LEVELS[idx + 1] })
    }
  },

  zoomOut: () => {
    const current = get().zoom
    const idx = ZOOM_LEVELS.indexOf(current)
    if (idx > 0) {
      set({ zoom: ZOOM_LEVELS[idx - 1] })
    }
  },

  setSelectedIndex: (selectedIndex) => set({ selectedIndex }),

  setTransition: (betweenIndex, type) => {
    set((state) => ({
      transitions: { ...state.transitions, [betweenIndex]: type },
    }))
  },

  updateSegmentDuration: (index, newDuration) => {
    set((state) => ({
      segments: state.segments.map((s) =>
        s.index === index
          ? { ...s, estimated_duration_sec: Math.max(1, Math.round(newDuration)) }
          : s
      ),
    }))
  },

  /**
   * Adjust the boundary between two consecutive segments.
   * @param betweenIndex - The index of the RIGHT segment (boundary between N-1 and N)
   * @param deltaSec - Positive = left segment gains time, right segment loses time
   */
  adjustBoundary: (betweenIndex, deltaSec) => {
    set((state) => {
      const segments = [...state.segments]
      const rightIdx = segments.findIndex((s) => s.index === betweenIndex)
      if (rightIdx <= 0 || rightIdx >= segments.length) return state

      const leftIdx = rightIdx - 1
      const left = segments[leftIdx]
      const right = segments[rightIdx]

      const maxRightDelta = right.estimated_duration_sec - 1
      const maxLeftDelta = left.estimated_duration_sec - 1
      const clampedDelta = Math.max(
        -maxLeftDelta,
        Math.min(deltaSec, maxRightDelta)
      )

      segments[leftIdx] = {
        ...left,
        estimated_duration_sec: Math.max(
          1,
          Math.round(left.estimated_duration_sec + clampedDelta)
        ),
      }
      segments[rightIdx] = {
        ...right,
        estimated_duration_sec: Math.max(
          1,
          Math.round(right.estimated_duration_sec - clampedDelta)
        ),
      }

      return { segments }
    })
  },

  reorderSegments: (fromIndex, toIndex) => {
    set((state) => {
      const list = [...state.segments]
      const fromIdx = list.findIndex((s) => s.index === fromIndex)
      const toIdx = list.findIndex((s) => s.index === toIndex)
      if (fromIdx === -1 || toIdx === -1) return state

      const [removed] = list.splice(fromIdx, 1)
      list.splice(toIdx, 0, removed)

      return {
        segments: list.map((s, i) => ({ ...s, index: i })),
      }
    })
  },
}))
