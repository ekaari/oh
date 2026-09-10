import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, FolderPlus, ShieldAlert } from 'lucide-react'
import { api, type DashboardStats, type Project } from '../api'

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [form, setForm] = useState({ name: '', base_url: 'https://example.com', description: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    const [s, p] = await Promise.all([api.dashboard(), api.projects()])
    setStats(s)
    setProjects(p)
  }

  useEffect(() => {
    load().catch((e) => setError(String(e)))
  }, [])

  async function onCreate(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.createProject(form)
      setForm({ name: '', base_url: 'https://example.com', description: '' })
      await load()
    } catch (err) {
      setError(String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-10">
      <section className="animate-rise relative overflow-hidden rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)]/70 px-6 py-10 sm:px-10">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              'linear-gradient(rgba(45,212,191,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(45,212,191,0.07) 1px, transparent 1px)',
            backgroundSize: '28px 28px',
            maskImage: 'radial-gradient(ellipse at center, black 20%, transparent 75%)',
          }}
        />
        <div className="relative max-w-2xl">
          <p className="font-[family-name:var(--font-display)] text-5xl sm:text-6xl tracking-tight text-[var(--color-foam)]">
            AI Web Tester
          </p>
          <h1 className="mt-3 text-xl sm:text-2xl font-medium text-teal-200/90">
            Virtual QA engineer for autonomous browser testing
          </h1>
          <p className="mt-3 text-[var(--color-mute)] leading-relaxed">
            Define a mission in natural language. The planner builds a test plan, Playwright explores the app,
            and verified bugs ship with evidence.
          </p>
        </div>
      </section>

      {stats && (
        <section className="animate-rise-delay grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            ['Projects', stats.projects],
            ['Passed', stats.tests_passed],
            ['Failed', stats.tests_failed],
            ['Runs', stats.runs],
          ].map(([label, value]) => (
            <div key={label as string} className="border border-[var(--color-line)] bg-[var(--color-panel)]/60 px-4 py-4">
              <div className="text-3xl font-semibold tracking-tight">{value as number}</div>
              <div className="text-xs uppercase tracking-[0.14em] text-[var(--color-mute)] mt-1">{label as string}</div>
            </div>
          ))}
        </section>
      )}

      <section className="grid lg:grid-cols-[1.1fr_0.9fr] gap-6">
        <div className="border border-[var(--color-line)] bg-[var(--color-panel)]/50 p-5">
          <div className="flex items-center gap-2 mb-4">
            <FolderPlus size={18} className="text-teal-300" />
            <h2 className="font-[family-name:var(--font-display)] text-2xl">New project</h2>
          </div>
          <form onSubmit={onCreate} className="space-y-3">
            <Field label="Name">
              <input
                required
                className="field"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Acme Admin"
              />
            </Field>
            <Field label="Base URL">
              <input
                required
                className="field"
                value={form.base_url}
                onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                placeholder="https://staging.example.com"
              />
            </Field>
            <Field label="Description">
              <textarea
                className="field min-h-20"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Optional notes"
              />
            </Field>
            {error && (
              <p className="text-sm text-rose-300 flex items-center gap-2">
                <ShieldAlert size={14} /> {error}
              </p>
            )}
            <button disabled={busy} className="btn-primary" type="submit">
              {busy ? 'Creating…' : 'Create project'}
            </button>
          </form>
        </div>

        <div className="border border-[var(--color-line)] bg-[var(--color-panel)]/50 p-5">
          <h2 className="font-[family-name:var(--font-display)] text-2xl mb-4">Projects</h2>
          <div className="space-y-2">
            {projects.length === 0 && (
              <p className="text-[var(--color-mute)] text-sm">No projects yet. Create one to start a mission.</p>
            )}
            {projects.map((p) => (
              <Link
                key={p.id}
                to={`/projects/${p.id}`}
                className="group flex items-center justify-between gap-3 border border-[var(--color-line)] px-3 py-3 no-underline text-[var(--color-foam)] hover:border-teal-400/40 hover:bg-teal-400/5 transition-colors"
              >
                <div>
                  <div className="font-medium">{p.name}</div>
                  <div className="text-xs text-[var(--color-mute)] truncate max-w-[280px]">{p.base_url}</div>
                </div>
                <ArrowRight size={16} className="text-[var(--color-mute)] group-hover:text-teal-300 transition-colors" />
              </Link>
            ))}
          </div>
        </div>
      </section>

      <style>{`
        .field {
          width: 100%;
          background: #0b1220;
          border: 1px solid var(--color-line);
          color: var(--color-foam);
          padding: 0.65rem 0.75rem;
          border-radius: 0.35rem;
          outline: none;
        }
        .field:focus { border-color: rgba(45,212,191,0.55); }
        .btn-primary {
          background: linear-gradient(180deg, #2dd4bf, #14b8a6);
          color: #06201c;
          font-weight: 600;
          border: 0;
          border-radius: 0.35rem;
          padding: 0.7rem 1rem;
          cursor: pointer;
        }
        .btn-primary:disabled { opacity: 0.6; cursor: wait; }
      `}</style>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="text-[var(--color-mute)] mb-1.5 block">{label}</span>
      {children}
    </label>
  )
}
