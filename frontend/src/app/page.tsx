'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import {
  Film,
  Sparkles,
  Download,
  ArrowRight,
  Github,
} from 'lucide-react'

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-zinc-950">
      {/* Navbar */}
      <header className="flex h-14 items-center justify-between border-b border-zinc-800 px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold text-sm">
          <span className="text-xl">🎬</span>
          Movie Narration
        </Link>
        <nav className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="text-sm text-zinc-400 hover:text-white transition-colors"
          >
            Dashboard
          </Link>
          <Link href="/login">
            <Button variant="ghost" size="sm">
              Sign In
            </Button>
          </Link>
          <Link href="/register">
            <Button size="sm">Get Started</Button>
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="flex flex-1 flex-col items-center justify-center px-4 py-20 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900 px-4 py-1.5 text-xs text-zinc-400">
          <Sparkles className="h-3.5 w-3.5 text-yellow-500" />
          AI-Powered Movie Narration Platform
        </div>

        <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
          Turn Any Movie Into a{' '}
          <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Viral Narration Video
          </span>
        </h1>

        <p className="mt-6 max-w-xl text-lg text-zinc-400">
          Choose a movie, pick a style, and let AI handle the rest — script
          writing, voiceover, scene matching, and multi-platform export. All in
          one click.
        </p>

        <div className="mt-10 flex items-center gap-4">
          <Link href="/register">
            <Button size="lg" className="gap-2">
              Start Creating Free
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="outline" size="lg">
              View Dashboard
            </Button>
          </Link>
        </div>

        {/* Stats */}
        <div className="mt-16 grid grid-cols-3 gap-8 text-center">
          {[
            { value: '50+', label: 'Movies' },
            { value: '12', label: 'Narration Styles' },
            { value: '4', label: 'Platform Export' },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="text-sm text-zinc-500">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-zinc-800 px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-2xl font-bold mb-12">
            How It Works
          </h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            {[
              {
                icon: Film,
                title: '1. Choose & Style',
                desc: 'Pick from 50 movies and 12 narration styles. AI understands each film\'s key scenes and plot points.',
              },
              {
                icon: Sparkles,
                title: '2. AI Generates',
                desc: '4-stage Agent pipeline writes the script, matches scenes, selects voiceover and BGM automatically.',
              },
              {
                icon: Download,
                title: '3. Export Anywhere',
                desc: 'One-click export to Douyin, Bilibili, Kuaishou, and Xiaohongshu with platform-optimized formatting.',
              },
            ].map((feat) => (
              <div
                key={feat.title}
                className="rounded-xl border border-zinc-800 bg-zinc-900 p-6"
              >
                <feat.icon className="h-8 w-8 text-blue-400 mb-4" />
                <h3 className="font-semibold mb-2">{feat.title}</h3>
                <p className="text-sm text-zinc-500">{feat.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800 px-6 py-8 text-center text-sm text-zinc-600">
        <div className="flex items-center justify-center gap-6">
          <Link href="/dashboard" className="hover:text-zinc-400 transition-colors">
            Dashboard
          </Link>
          <Link href="/login" className="hover:text-zinc-400 transition-colors">
            Sign In
          </Link>
          <a
            href="https://github.com/bluekey2020/movie-narration-web"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 hover:text-zinc-400 transition-colors"
          >
            <Github className="h-4 w-4" />
            GitHub
          </a>
        </div>
        <p className="mt-4">Movie Narration Web — AI电影解说一键出片平台</p>
      </footer>
    </div>
  )
}
