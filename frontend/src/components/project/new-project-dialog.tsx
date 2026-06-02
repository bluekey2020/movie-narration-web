'use client'

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { moviesApi, stylesApi, type Movie, type StyleFingerprint, type Platform } from '@/lib/api'
import { Search, Loader2, AlertCircle, RefreshCw } from 'lucide-react'

const PLATFORMS: { value: Platform; label: string; desc: string }[] = [
  { value: 'douyin', label: 'Douyin', desc: 'Vertical, fast-paced, strong hooks' },
  { value: 'bilibili', label: 'Bilibili', desc: 'Horizontal, in-depth, informative' },
  { value: 'kuaishou', label: 'Kuaishou', desc: 'Vertical, down-to-earth, casual' },
  { value: 'xiaohongshu', label: 'Xiaohongshu', desc: 'Vertical, emotional, aesthetic' },
]

// Fallback mock data for when backend is unavailable (frontend-only testing)
const MOCK_MOVIES: Movie[] = [
  { movie_id: 'shawshank_redemption', title: '肖申克的救赎', year: 1994, genre: ['剧情', '犯罪'], rating: 9.7, duration: 142, plot_summary: '', key_scenes: [], character_list: [], hot_topics: [] },
  { movie_id: 'farewell_my_concubine', title: '霸王别姬', year: 1993, genre: ['剧情', '历史'], rating: 9.6, duration: 171, plot_summary: '', key_scenes: [], character_list: [], hot_topics: [] },
  { movie_id: 'inception', title: '盗梦空间', year: 2010, genre: ['科幻', '悬疑'], rating: 9.3, duration: 148, plot_summary: '', key_scenes: [], character_list: [], hot_topics: [] },
  { movie_id: 'titanic', title: '泰坦尼克号', year: 1997, genre: ['爱情', '灾难'], rating: 9.4, duration: 194, plot_summary: '', key_scenes: [], character_list: [], hot_topics: [] },
  { movie_id: 'the_godfather', title: '教父', year: 1972, genre: ['剧情', '犯罪'], rating: 9.3, duration: 175, plot_summary: '', key_scenes: [], character_list: [], hot_topics: [] },
  { movie_id: 'forrest_gump', title: '阿甘正传', year: 1994, genre: ['剧情', '爱情'], rating: 9.5, duration: 142, plot_summary: '', key_scenes: [], character_list: [], hot_topics: [] },
  { movie_id: 'spirited_away', title: '千与千寻', year: 2001, genre: ['动画', '奇幻'], rating: 9.4, duration: 125, plot_summary: '', key_scenes: [], character_list: [], hot_topics: [] },
  { movie_id: 'the_dark_knight', title: '蝙蝠侠：黑暗骑士', year: 2008, genre: ['动作', '犯罪'], rating: 9.2, duration: 152, plot_summary: '', key_scenes: [], character_list: [], hot_topics: [] },
]

const MOCK_STYLES: StyleFingerprint[] = [
  { style_id: 'action_hot', name: '热血动作', description: '高频动词+短句+极速节奏，适配动作/超英/战争片' },
  { style_id: 'suspense_brainburn', name: '烧脑悬疑', description: '设问句式+层层递进+信息密度高，适配悬疑/推理/犯罪片' },
  { style_id: 'comedy', name: '爆笑喜剧', description: '反转句式+夸张比喻+网络热梗，适配喜剧/荒诞片' },
  { style_id: 'inspirational', name: '励志成长', description: '低谷→转折→高光弧线，适配传记/体育/青春片' },
  { style_id: 'emotional_life', name: '情感人生', description: '共情叙事+细节放大+普世连接，适配爱情/文艺片' },
  { style_id: 'scifi_fantasy', name: '奇幻科幻', description: '世界观简化+想象力激发，适配科幻/奇幻片' },
] as StyleFingerprint[]

interface NewProjectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreate: (params: {
    movie_id: string
    movie_title: string
    style_id: string
    style_name: string
    platform: Platform
  }) => void
}

export function NewProjectDialog({
  open,
  onOpenChange,
  onCreate,
}: NewProjectDialogProps) {
  const [step, setStep] = useState(0)
  const [movies, setMovies] = useState<Movie[]>([])
  const [styles, setStyles] = useState<StyleFingerprint[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null)
  const [selectedStyle, setSelectedStyle] = useState<StyleFingerprint | null>(null)
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('douyin')
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [usingFallback, setUsingFallback] = useState(false)

  useEffect(() => {
    if (open) {
      setStep(0)
      setSelectedMovie(null)
      setSelectedStyle(null)
      setSearchQuery('')
      setLoadError(null)
      setUsingFallback(false)
      loadData()
    }
  }, [open])

  async function loadData() {
    setIsLoading(true)
    setLoadError(null)

    try {
      const [movieRes, styleRes] = await Promise.all([
        moviesApi.list(),
        stylesApi.list(),
      ])

      if (movieRes.success && movieRes.data && movieRes.data.length > 0) {
        setMovies(movieRes.data)
      } else {
        // API returned empty or error — use fallback
        setMovies(MOCK_MOVIES)
        setUsingFallback(true)
      }

      if (styleRes.success && styleRes.data && styleRes.data.length > 0) {
        setStyles(styleRes.data)
      } else {
        setStyles(MOCK_STYLES)
        setUsingFallback(true)
      }
    } catch {
      // Network error — use fallback mock data
      setMovies(MOCK_MOVIES)
      setStyles(MOCK_STYLES)
      setUsingFallback(true)
      setLoadError('Backend unavailable — using demo data. Start the backend for full functionality.')
    }

    setIsLoading(false)
  }

  const filteredMovies = searchQuery
    ? movies.filter(
        (m) =>
          m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          m.genre.some((g) => g.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : movies

  function handleNext() {
    if (step < 2) {
      setStep(step + 1)
    } else {
      if (selectedMovie && selectedStyle) {
        onCreate({
          movie_id: selectedMovie.movie_id,
          movie_title: selectedMovie.title,
          style_id: selectedStyle.style_id,
          style_name: selectedStyle.name,
          platform: selectedPlatform,
        })
        onOpenChange(false)
      }
    }
  }

  function handleBack() {
    if (step > 0) setStep(step - 1)
  }

  const canProceed =
    (step === 0 && selectedMovie) ||
    (step === 1 && selectedStyle) ||
    step === 2

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
            <p className="text-sm text-zinc-500">Loading movies and styles...</p>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>New Project</DialogTitle>
              <DialogDescription>
                Step {step + 1} of 3 —
                {step === 0 && ' Choose a movie'}
                {step === 1 && ' Pick a narration style'}
                {step === 2 && ' Select target platform'}
              </DialogDescription>
            </DialogHeader>

            {/* Backend unavailable warning */}
            {loadError && (
              <div className="flex items-start gap-2 rounded-lg bg-amber-900/30 border border-amber-800/50 p-3 text-sm text-amber-300">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p>{loadError}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0 text-amber-400"
                  onClick={loadData}
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}

            {usingFallback && !loadError && (
              <div className="flex items-center gap-2 rounded-lg bg-blue-900/30 border border-blue-800/50 p-2 text-xs text-blue-300">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                Using demo data — connect backend for full movie library
              </div>
            )}

            {/* Step 0: Movie Selection */}
            {step === 0 && (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                  <Input
                    placeholder="Search movies..."
                    className="pl-9"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <div className="max-h-64 space-y-1 overflow-y-auto">
                  {filteredMovies.map((movie) => (
                    <button
                      key={movie.movie_id}
                      className={`w-full rounded-lg p-3 text-left transition-colors ${
                        selectedMovie?.movie_id === movie.movie_id
                          ? 'bg-zinc-800 ring-1 ring-zinc-600'
                          : 'hover:bg-zinc-800/50'
                      }`}
                      onClick={() => setSelectedMovie(movie)}
                    >
                      <div className="font-medium text-sm">{movie.title}</div>
                      <div className="text-xs text-zinc-500 mt-1">
                        {movie.year} · ⭐ {movie.rating} ·{' '}
                        {movie.genre.join(', ')}
                      </div>
                    </button>
                  ))}
                  {filteredMovies.length === 0 && (
                    <p className="text-center text-sm text-zinc-500 py-8">
                      No movies found
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Step 1: Style Selection */}
            {step === 1 && (
              <div className="max-h-64 space-y-2 overflow-y-auto">
                {styles.map((style) => (
                  <button
                    key={style.style_id}
                    className={`w-full rounded-lg p-3 text-left transition-colors ${
                      selectedStyle?.style_id === style.style_id
                        ? 'bg-zinc-800 ring-1 ring-zinc-600'
                        : 'hover:bg-zinc-800/50'
                    }`}
                    onClick={() => setSelectedStyle(style)}
                  >
                    <div className="font-medium text-sm">{style.name}</div>
                    <div className="text-xs text-zinc-500 mt-1">
                      {style.description}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Step 2: Platform Selection */}
            {step === 2 && (
              <div className="space-y-2">
                {PLATFORMS.map((platform) => (
                  <button
                    key={platform.value}
                    className={`w-full rounded-lg p-3 text-left transition-colors ${
                      selectedPlatform === platform.value
                        ? 'bg-zinc-800 ring-1 ring-zinc-600'
                        : 'hover:bg-zinc-800/50'
                    }`}
                    onClick={() => setSelectedPlatform(platform.value)}
                  >
                    <div className="font-medium text-sm">{platform.label}</div>
                    <div className="text-xs text-zinc-500 mt-0.5">
                      {platform.desc}
                    </div>
                  </button>
                ))}
              </div>
            )}

            <DialogFooter className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={handleBack}
                disabled={step === 0}
              >
                Back
              </Button>
              <Button onClick={handleNext} disabled={!canProceed}>
                {step === 2 ? 'Create Project' : 'Next'}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
