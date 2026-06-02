'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Film,
  PlusCircle,
  Settings,
  LogOut,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useUserStore } from '@/stores/user-store'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard?tab=projects', label: 'My Projects', icon: Film },
]

export function Sidebar() {
  const pathname = usePathname()
  const { user, logout } = useUserStore()

  return (
    <aside className="flex h-full w-64 flex-col border-r border-zinc-800 bg-zinc-950">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-zinc-800 px-4">
        <span className="text-xl">🎬</span>
        <Link href="/dashboard" className="font-semibold text-sm">
          Movie Narration
        </Link>
      </div>

      {/* Nav items */}
      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-zinc-800 text-white'
                  : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* User section */}
      <div className="border-t border-zinc-800 p-3">
        {user ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-800 text-sm">
                {user.display_name[0]}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">
                  {user.display_name}
                </p>
                <p className="text-xs text-zinc-500 truncate">{user.email}</p>
              </div>
            </div>
            <div className="flex gap-1">
              <Link href="/settings" className="flex-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full text-xs text-zinc-400"
                >
                  <Settings className="h-3 w-3 mr-1" />
                  Settings
                </Button>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 text-xs text-zinc-400"
                onClick={logout}
              >
                <LogOut className="h-3 w-3 mr-1" />
                Logout
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <Link href="/login">
              <Button className="w-full" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/register">
              <Button variant="outline" className="w-full" size="sm">
                Sign Up
              </Button>
            </Link>
          </div>
        )}
      </div>
    </aside>
  )
}
