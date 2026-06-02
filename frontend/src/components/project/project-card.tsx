'use client'

import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { type Project, type ProjectStatus } from '@/lib/api'
import { Film, Clock, MoreVertical } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'

const STATUS_LABELS: Record<ProjectStatus, string> = {
  draft: 'Draft',
  selecting: 'Selecting Movie',
  scripting: 'Generating Script',
  voicing: 'Generating Voice',
  composing: 'Composing Video',
  reviewing: 'Ready to Review',
  completed: 'Completed',
  failed: 'Failed',
}

const STATUS_COLORS: Record<ProjectStatus, string> = {
  draft: 'bg-zinc-600',
  selecting: 'bg-blue-600',
  scripting: 'bg-purple-600',
  voicing: 'bg-indigo-600',
  composing: 'bg-orange-600',
  reviewing: 'bg-yellow-600',
  completed: 'bg-green-600',
  failed: 'bg-red-600',
}

interface ProjectCardProps {
  project: Project
  onDelete: (id: string) => void
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const timeAgo = getTimeAgo(project.updated_at)

  return (
    <Link href={`/project/${project.project_id}`}>
      <Card className="group cursor-pointer border-zinc-800 bg-zinc-900 transition-colors hover:border-zinc-700 hover:bg-zinc-900/80">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-800">
                <Film className="h-5 w-5 text-zinc-400" />
              </div>
              <div className="min-w-0">
                <h3 className="font-medium text-sm truncate">
                  {project.movie_title}
                </h3>
                <p className="text-xs text-zinc-500 mt-0.5">
                  {project.style_name} · {project.platform}
                </p>
              </div>
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity inline-flex items-center justify-center rounded-lg hover:bg-zinc-800"
                onClick={(e) => e.preventDefault()}
              >
                <MoreVertical className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  className="text-red-400 text-xs"
                  onClick={(e) => {
                    e.preventDefault()
                    onDelete(project.project_id)
                  }}
                >
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <div className="flex items-center gap-2 mt-3">
            <span
              className={`h-1.5 w-1.5 rounded-full ${STATUS_COLORS[project.status]}`}
            />
            <span className="text-xs text-zinc-400">
              {STATUS_LABELS[project.status]}
            </span>
            <span className="text-xs text-zinc-600">·</span>
            <Clock className="h-3 w-3 text-zinc-600" />
            <span className="text-xs text-zinc-600">{timeAgo}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}

function getTimeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}
