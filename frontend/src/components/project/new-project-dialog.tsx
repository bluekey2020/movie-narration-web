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
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { moviesApi, stylesApi, type Movie, type StyleFingerprint, type Platform } from '@/lib/api'
import { Search, Loader2 } from 'lucide-react'

const PLATFORMS: { value: Platform; label: string; desc: string }[] = [
  { value: 'douyin', label: 'Douyin', desc: 'Vertical, fast-paced, strong hooks' },
  { value: 'bilibili', label: 'Bilibili', desc: 'Horizontal, in-depth, informative' },
  { value: 'kuaishou', label: 'Kuaishou', desc: 'Vertical, down-to-earth, casual' },
  { value: 'xiaohongshu', label: 'Xiaohongshu', desc: 'Vertical, emotional, aesthetic' },
]

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
  // Step: movie → style → platform → confirm
  const [step, setStep] = useState(0)
  const [movies, setMovies] = useState<Movie[]>([])
  const [styles, setStyles] = useState<StyleFingerprint[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null)
  const [selectedStyle, setSelectedStyle] = useState<StyleFingerprint | null>(null)
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('douyin')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (open) {
      setStep(0)
      setSelectedMovie(null)
      setSelectedStyle(null)
      setSearchQuery('')
      loadData()
    }
  }, [open])

  async function loadData() {
    setIsLoading(true)
    const [movieRes, styleRes] = await Promise.all([
      moviesApi.list(),
      stylesApi.list(),
    ])
    if (movieRes.success && movieRes.data) setMovies(movieRes.data)
    if (styleRes.success && styleRes.data) setStyles(styleRes.data)
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
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
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
