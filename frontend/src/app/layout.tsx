import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Movie Narration Web - AI电影解说工作台',
  description: '专为电影解说创作者打造的一站式AI创作平台',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-zinc-950 text-white antialiased">
        {children}
      </body>
    </html>
  )
}
