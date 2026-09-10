import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { KeyRound, Play, Radar, Server } from 'lucide-react'
import {
  api,
  type Credential,
  type Environment,
  type Mission,
  type Project,
  type TestRun,
} from '../api'

export function ProjectPage() {
  const { projectId = '' } = useParams()
  const [project, setProject] = useState<Project | null>(null)
  const [envs, setEnvs] = useState<Environment[]>([])
  const [creds, setCreds] = useState<Credential[]>([])
  const [missions, setMissions] = useState<Mission[]>([])
  const [runsByMission, setRunsByMission] = useState<Record<string, TestRun[]>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [envForm, setEnvForm] = useState({
    name: 'Staging',
    env_type: 'Staging',
    base_url: '',
    safety_level: 'SAFE',
  })
  const [credForm, setCredForm] = useState({
    name: 'Default login',
    auth_type: 'username_password',
    username: '',
    password: '',
    login_url: '',
  })
  const [missionForm, setMissionForm] = useState({
    title: 'Exploratory QA',
    mission_text:
      'Explore the application, validate forms, check navigation, and report verified bugs with evidence.',
    environment_id: '',
    credential_id: '',
  })

  async function load() {
    const projects = await api.projects()
    const p = projects.find((x) => x.id === projectId) || null
    setProject(p)
    if (!p) return
    const [e, c, m] = await Promise.all([
      api.environments(projectId),
      api.credentials(projectId),
      api.missions(projectId),
    ])
    setEnvs(e)
    setCreds(c)
    setMissions(m)
    setEnvForm((f) => ({ ...f, base_url: f.base_url || p.base_url }))
    if (!missionForm.environment_id && e[0]) {
      setMissionForm((f) => ({ ...f, environment_id: e[0].id }))
    }
    const runMap: Record<string, TestRun[]> = {}
    await Promise.all(
      m.map(async (mis) => {
        runMap[mis.id] = await api.runs(mis.id)
      }),
    )
    setRunsByMission(runMap)
  }

  useEffect(() => {
    load().catch((e) => setError(String(e)))
    const t = setInterval(() => {
      load().catch(() => undefined)
    }, 2500)
    return () => clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const activeLifecycle = useMemo(() => {
    for (const runs of Object.values(runsByMission)) {
      const live = runs.find((r) => !['COMPLETED', 'ERROR'].includes(r.lifecycle))
      if (live) return live
    }
    return null
  }, [runsByMission])

  if (!project) {
    return <p className="text-[var(--color-mute)]">{error || 'Loading project…'}</p>
  }

  return (
    <div className="space-y-8 animate-rise">
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-teal-300/80">Project</p>
        <h1 className="font-[family-name:var(--font-display)] text-4xl mt-1">{project.name}</h1>
        <p className="text-[var(--color-mute)] mt-1">{project.base_url}</p>
        {activeLifecycle && (
          <p className="mt-3 inline-flex items-center gap-2 text-sm text-amber-200">
            <span className="live-dot h-2 w-2 rounded-full bg-amber-300 inline-block" />
            Live run {activeLifecycle.id} · {activeLifecycle.lifecycle}
          </p>
        )}
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <Panel title="Environment" icon={<Server size={16} />}>
          <form
            className="space-y-2"
            onSubmit={async (e) => {
              e.preventDefault()
              setBusy(true)
              try {
                await api.createEnvironment(projectId, envForm)
                await load()
              } catch (err) {
                setError(String(err))
              } finally {
                setBusy(false)
              }
            }}
          >
            <input className="field" value={envForm.name} onChange={(e) => setEnvForm({ ...envForm, name: e.target.value })} placeholder="Name" />
            <select className="field" value={envForm.env_type} onChange={(e) => setEnvForm({ ...envForm, env_type: e.target.value })}>
              {['Development', 'Staging', 'Production', 'Local', 'Custom'].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
            <input className="field" value={envForm.base_url} onChange={(e) => setEnvForm({ ...envForm, base_url: e.target.value })} placeholder="Base URL" />
            <select className="field" value={envForm.safety_level} onChange={(e) => setEnvForm({ ...envForm, safety_level: e.target.value })}>
              {['SAFE', 'WARNING', 'DANGEROUS'].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
            <button className="btn-secondary" disabled={busy}>Add environment</button>
          </form>
          <ul className="mt-3 space-y-1 text-sm">
            {envs.map((e) => (
              <li key={e.id} className="text-[var(--color-mute)]">
                {e.name} · {e.safety_level} · {e.base_url}
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="Authentication" icon={<KeyRound size={16} />}>
          <form
            className="space-y-2"
            onSubmit={async (e) => {
              e.preventDefault()
              setBusy(true)
              try {
                await api.createCredential(projectId, credForm)
                setCredForm({ ...credForm, password: '' })
                await load()
              } catch (err) {
                setError(String(err))
              } finally {
                setBusy(false)
              }
            }}
          >
            <input className="field" value={credForm.name} onChange={(e) => setCredForm({ ...credForm, name: e.target.value })} placeholder="Name" />
            <input className="field" value={credForm.login_url} onChange={(e) => setCredForm({ ...credForm, login_url: e.target.value })} placeholder="Login URL (optional)" />
            <input className="field" value={credForm.username} onChange={(e) => setCredForm({ ...credForm, username: e.target.value })} placeholder="Username" />
            <input className="field" type="password" value={credForm.password} onChange={(e) => setCredForm({ ...credForm, password: e.target.value })} placeholder="Password (encrypted at rest)" />
            <button className="btn-secondary" disabled={busy}>Save credential</button>
          </form>
          <ul className="mt-3 space-y-1 text-sm">
            {creds.map((c) => (
              <li key={c.id} className="text-[var(--color-mute)]">
                {c.name} · {c.username || '—'} · password {c.has_password ? '••••' : 'none'}
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="AI Test Mission" icon={<Radar size={16} />}>
          <form
            className="space-y-2"
            onSubmit={async (e) => {
              e.preventDefault()
              setBusy(true)
              try {
                const mission = await api.createMission(projectId, {
                  title: missionForm.title,
                  mission_text: missionForm.mission_text,
                  environment_id: missionForm.environment_id || undefined,
                  credential_id: missionForm.credential_id || undefined,
                })
                await api.startMission(mission.id)
                await load()
              } catch (err) {
                setError(String(err))
              } finally {
                setBusy(false)
              }
            }}
          >
            <input className="field" value={missionForm.title} onChange={(e) => setMissionForm({ ...missionForm, title: e.target.value })} placeholder="Mission title" />
            <textarea className="field min-h-28" value={missionForm.mission_text} onChange={(e) => setMissionForm({ ...missionForm, mission_text: e.target.value })} />
            <select className="field" value={missionForm.environment_id} onChange={(e) => setMissionForm({ ...missionForm, environment_id: e.target.value })}>
              <option value="">Default project URL</option>
              {envs.map((e) => (
                <option key={e.id} value={e.id}>{e.name}</option>
              ))}
            </select>
            <select className="field" value={missionForm.credential_id} onChange={(e) => setMissionForm({ ...missionForm, credential_id: e.target.value })}>
              <option value="">No authentication</option>
              {creds.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <button className="btn-primary inline-flex items-center gap-2" disabled={busy}>
              <Play size={14} /> {busy ? 'Starting…' : 'Create & start test'}
            </button>
          </form>
        </Panel>
      </div>

      {error && <p className="text-rose-300 text-sm">{error}</p>}

      <section className="border border-[var(--color-line)] bg-[var(--color-panel)]/50 p-5">
        <h2 className="font-[family-name:var(--font-display)] text-2xl mb-4">Missions & history</h2>
        <div className="space-y-4">
          {missions.length === 0 && <p className="text-sm text-[var(--color-mute)]">No missions yet.</p>}
          {missions.map((m) => (
            <div key={m.id} className="border border-[var(--color-line)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-medium">{m.title}</div>
                  <div className="text-sm text-[var(--color-mute)] mt-1 max-w-3xl">{m.mission_text}</div>
                  <div className="text-xs text-teal-300/80 mt-2">Status: {m.status}</div>
                </div>
              </div>
              <div className="mt-3 space-y-2">
                {(runsByMission[m.id] || []).map((r) => (
                  <Link
                    key={r.id}
                    to={`/runs/${r.id}`}
                    className="flex items-center justify-between gap-3 text-sm no-underline text-[var(--color-foam)] border border-transparent hover:border-[var(--color-line)] px-2 py-2"
                  >
                    <span>
                      {r.id} · {r.lifecycle}
                      {r.is_regression ? ' · regression' : ''}
                    </span>
                    <span className="text-[var(--color-mute)]">
                      P{r.summary?.passed ?? 0} / F{r.summary?.failed ?? 0} / B{r.bugs?.length ?? 0}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <style>{`
        .field {
          width: 100%;
          background: #0b1220;
          border: 1px solid var(--color-line);
          color: var(--color-foam);
          padding: 0.55rem 0.7rem;
          border-radius: 0.35rem;
          outline: none;
          font: inherit;
        }
        .field:focus { border-color: rgba(45,212,191,0.55); }
        .btn-primary {
          background: linear-gradient(180deg, #2dd4bf, #14b8a6);
          color: #06201c;
          font-weight: 600;
          border: 0;
          border-radius: 0.35rem;
          padding: 0.65rem 0.9rem;
          cursor: pointer;
        }
        .btn-secondary {
          background: transparent;
          color: var(--color-foam);
          border: 1px solid var(--color-line);
          border-radius: 0.35rem;
          padding: 0.55rem 0.8rem;
          cursor: pointer;
        }
      `}</style>
    </div>
  )
}

function Panel({
  title,
  icon,
  children,
}: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="border border-[var(--color-line)] bg-[var(--color-panel)]/50 p-4">
      <div className="flex items-center gap-2 mb-3 text-teal-200">
        {icon}
        <h2 className="font-[family-name:var(--font-display)] text-xl text-[var(--color-foam)]">{title}</h2>
      </div>
      {children}
    </div>
  )
}
