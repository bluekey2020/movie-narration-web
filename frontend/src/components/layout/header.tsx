'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { PlusCircle } from 'lucide-react'
import { useUserStore } from '@/stores/user-store'

interface HeaderProps {
  title?: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function Header({ title, action }: HeaderProps) {
  const { user } = useUserStore()

  return (
    <header className="flex h-14 items-center justify-between border-b border-zinc-800 bg-zinc-950 px-6">
      <div className="flex items-center gap-3">
        {title && <h1 className="text-sm font-medium">{title}</h1>}
      </div>

      <div className="flex items-center gap-3">
        {action && (
          <Button size="sm" onClick={action.onClick}>
            <PlusCircle className="h-4 w-4 mr-1" />
            {action.label}
          </Button>
        )}

        {user && (
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <span>
              {user.monthly_videos_used}/{user.monthly_videos_limit} videos
            </span>
            <span className="text-zinc-700">|</span>
            <span>{user.credits_remaining} credits</span>
          </div>
        )}
      </div>
    </header>
  )
}
