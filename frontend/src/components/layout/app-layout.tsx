'use client'

import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'

interface AppLayoutProps {
  children: React.ReactNode
  title?: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function AppLayout({ children, title, action }: AppLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title={title} action={action} />
        <main className="flex-1 overflow-y-auto bg-zinc-950 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
