import type { Metadata } from 'next'
import './globals.css'
import { Geist } from 'next/font/google'
import { cn } from '@/lib/utils'
import { TooltipProvider } from '@/components/ui/tooltip'

const geist = Geist({ subsets: ['latin'], variable: '--font-sans' })

export const metadata: Metadata = {
  title: 'Movie Narration Web — AI Movie Narration Workbench',
  description:
    'A one-stop AI-powered platform for movie narration video creation',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className={cn('font-sans', geist.variable)}>
      <body className="min-h-screen bg-zinc-950 text-white antialiased">
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  )
}
