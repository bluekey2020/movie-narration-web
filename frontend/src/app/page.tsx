'use client'

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-4">🎬 Movie Narration Web</h1>
      <p className="text-zinc-400 text-lg mb-8">
        专为电影解说创作者打造的一站式 AI 创作平台
      </p>
      <div className="grid grid-cols-3 gap-6 max-w-3xl">
        {[
          { title: '智能选片', desc: '搜索/推荐/热点追踪' },
          { title: 'AI文案生成', desc: '4层Agent协作+风格指纹' },
          { title: '一键出片', desc: '配音→画面→合成→导出' },
        ].map((feat) => (
          <div
            key={feat.title}
            className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 text-center hover:border-zinc-700 transition-colors"
          >
            <h3 className="font-semibold mb-2">{feat.title}</h3>
            <p className="text-sm text-zinc-500">{feat.desc}</p>
          </div>
        ))}
      </div>
    </main>
  )
}
