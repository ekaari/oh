import { NavLink, Outlet } from 'react-router-dom'
import { Activity, Bot } from 'lucide-react'

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-[var(--color-line)]/80 backdrop-blur-md sticky top-0 z-20 bg-[color-mix(in_oklab,var(--color-ink)_82%,transparent)]">
        <div className="mx-auto max-w-6xl px-5 py-4 flex items-center justify-between gap-4">
          <NavLink to="/" className="flex items-center gap-3 no-underline text-[var(--color-foam)]">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-teal-400/30 bg-teal-400/10 text-teal-300">
              <Bot size={18} />
            </span>
            <span>
              <span className="block font-[family-name:var(--font-display)] text-2xl leading-none tracking-tight">
                AI Web Tester
              </span>
              <span className="text-xs text-[var(--color-mute)]">Explore → Test → Detect → Verify → Document</span>
            </span>
          </NavLink>
          <div className="hidden sm:flex items-center gap-2 text-xs text-[var(--color-mute)]">
            <Activity size={14} className="text-teal-300" />
            Autonomous QA Platform
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-8">
        <Outlet />
      </main>
    </div>
  )
}
