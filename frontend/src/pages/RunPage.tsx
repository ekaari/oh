import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { MessageSquare, RefreshCw, FileText } from 'lucide-react'
import { api, type TestRun } from '../api'

const SEV_COLOR: Record<string, string> = {
  CRITICAL: 'text-rose-300',
  HIGH: 'text-rose-200',
  MEDIUM: 'text-amber-200',
  LOW: 'text-teal-200',
  INFO: 'text-sky-200',
}

export function RunPage() {
  const { runId = '' } = useParams()
  const [run, setRun] = useState<TestRun | null>(null)
  const [question, setQuestion] = useState('Bug paling serius apa?')
  const [answer, setAnswer] = useState<string | null>(null)
  const [askError, setAskError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [asking, setAsking] = useState(false)

  async function load() {
    const data = await api.run(runId)
    setRun(data)
  }

  useEffect(() => {
    load().catch((e) => setError(String(e)))
    const t = setInterval(() => {
      load().catch(() => undefined)
    }, 2000)
    return () => clearInterval(t)
  }, [runId])

  if (!run) {
    return <p className="text-[var(--color-mute)]">{error || 'Loading run…'}</p>
  }

  const live = !['COMPLETED', 'ERROR'].includes(run.lifecycle)

  return (
    <div className="space-y-8 animate-rise">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-teal-300/80">Test run</p>
          <h1 className="font-[family-name:var(--font-display)] text-4xl mt-1">{run.id}</h1>
          <p className="text-[var(--color-mute)] mt-1 flex items-center gap-2">
            {live && <span className="live-dot h-2 w-2 rounded-full bg-amber-300 inline-block" />}
            Lifecycle: <span className="text-[var(--color-foam)]">{run.lifecycle}</span>
            {run.is_regression && ' · regression'}
          </p>
          {run.error_message && <p className="text-rose-300 text-sm mt-2">{run.error_message}</p>}
        </div>
        <div className="flex gap-2">
          {run.report_path && (
            <a className="btn-secondary inline-flex items-center gap-2 no-underline" href={`/api/runs/${run.id}/report`} target="_blank" rel="noreferrer">
              <FileText size={14} /> HTML report
            </a>
          )}
          <button
            className="btn-primary inline-flex items-center gap-2"
            disabled={busy || live}
            onClick={async () => {
              setBusy(true)
              try {
                await api.retest(run.id)
              } catch (e) {
                setError(String(e))
              } finally {
                setBusy(false)
              }
            }}
          >
            <RefreshCw size={14} /> Re-test
          </button>
        </div>
      </div>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          ['Passed', run.summary?.passed ?? 0],
          ['Failed', run.summary?.failed ?? 0],
          ['Blocked', run.summary?.blocked ?? 0],
          ['Bugs', run.bugs?.length ?? 0],
        ].map(([k, v]) => (
          <div key={k as string} className="border border-[var(--color-line)] bg-[var(--color-panel)]/60 px-4 py-4">
            <div className="text-3xl font-semibold">{v as number}</div>
            <div className="text-xs uppercase tracking-[0.14em] text-[var(--color-mute)] mt-1">{k as string}</div>
          </div>
        ))}
      </section>

      <div className="grid lg:grid-cols-2 gap-4">
        <section className="border border-[var(--color-line)] bg-[var(--color-panel)]/50 p-5">
          <h2 className="font-[family-name:var(--font-display)] text-2xl mb-3">Steps</h2>
          <div className="space-y-2">
            {(run.steps || []).map((s) => (
              <div key={s.id} className="border border-[var(--color-line)] px-3 py-2">
                <div className="flex justify-between gap-3 text-sm">
                  <span>{s.title}</span>
                  <span className={s.status === 'PASSED' ? 'text-teal-300' : s.status === 'FAILED' ? 'text-rose-300' : 'text-[var(--color-mute)]'}>
                    {s.status}
                  </span>
                </div>
                {s.detail && <p className="text-xs text-[var(--color-mute)] mt-1">{s.detail}</p>}
              </div>
            ))}
            {(!run.steps || run.steps.length === 0) && (
              <p className="text-sm text-[var(--color-mute)]">Waiting for planner / browser agent…</p>
            )}
          </div>
        </section>

        <section className="border border-[var(--color-line)] bg-[var(--color-panel)]/50 p-5">
          <h2 className="font-[family-name:var(--font-display)] text-2xl mb-3">Application map</h2>
          <ul className="space-y-1 text-sm">
            {(run.application_map?.pages || []).map((p, i) => (
              <li key={`${p.url}-${i}`} className="text-[var(--color-mute)]">
                <span className="text-[var(--color-foam)]">{p.title || 'Untitled'}</span> · {p.url}
              </li>
            ))}
            {!(run.application_map?.pages || []).length && (
              <li className="text-[var(--color-mute)]">No pages yet</li>
            )}
          </ul>
        </section>
      </div>

      <section className="border border-[var(--color-line)] bg-[var(--color-panel)]/50 p-5">
        <h2 className="font-[family-name:var(--font-display)] text-2xl mb-3">Verified bugs</h2>
        <div className="space-y-3">
          {(run.bugs || []).map((b) => (
            <div key={b.id} className="border border-[var(--color-line)] p-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className={`font-semibold ${SEV_COLOR[b.severity] || ''}`}>{b.severity}</span>
                <span className="text-[var(--color-mute)]">{b.category}</span>
                {b.verified && <span className="text-teal-300 text-xs">verified</span>}
              </div>
              <div className="mt-1 font-medium">{b.title}</div>
              {b.actual_result && <p className="text-sm text-[var(--color-mute)] mt-1">{b.actual_result}</p>}
              {!!b.reproduction_steps?.length && (
                <ol className="mt-2 text-xs text-[var(--color-mute)] list-decimal pl-4 space-y-1">
                  {b.reproduction_steps.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ol>
              )}
            </div>
          ))}
          {(!run.bugs || run.bugs.length === 0) && (
            <p className="text-sm text-[var(--color-mute)]">No verified bugs for this run.</p>
          )}
        </div>
      </section>

      <section className="border border-[var(--color-line)] bg-[var(--color-panel)]/50 p-5">
        <h2 className="font-[family-name:var(--font-display)] text-2xl mb-3">Evidence</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {(run.evidences || []).map((e) => (
            <div key={e.id} className="border border-[var(--color-line)] p-2">
              <div className="text-xs text-[var(--color-mute)] mb-2">{e.evidence_type} · {e.url}</div>
              {e.path?.endsWith('.png') && (
                <img src={`/api/files/${e.id}`} alt="evidence" className="w-full border border-[var(--color-line)]" />
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="border border-[var(--color-line)] bg-[var(--color-panel)]/50 p-5">
        <div className="flex items-center gap-2 mb-3">
          <MessageSquare size={16} className="text-teal-300" />
          <h2 className="font-[family-name:var(--font-display)] text-2xl">Ask about this run</h2>
        </div>
        <form
          className="flex flex-col sm:flex-row gap-2"
          onSubmit={async (e) => {
            e.preventDefault()
            if (!question.trim() || asking) return
            setAsking(true)
            setAskError(null)
            try {
              const res = await api.query({ question: question.trim(), run_id: run.id })
              setAnswer(res.answer)
            } catch (err) {
              setAskError(String(err))
              setAnswer(null)
            } finally {
              setAsking(false)
            }
          }}
        >
          <input
            className="field flex-1"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={asking}
          />
          <button className="btn-primary" disabled={asking || !question.trim()} type="submit">
            {asking ? 'Asking…' : 'Ask'}
          </button>
        </form>
        {askError && <p className="mt-3 text-sm text-rose-300">{askError}</p>}
        {answer && (
          <pre className="mt-3 whitespace-pre-wrap text-sm text-[var(--color-foam)] border border-[var(--color-line)] bg-[#0b1220] p-3 rounded-sm">
            {answer}
          </pre>
        )}
      </section>

      <p className="text-sm text-[var(--color-mute)]">
        Mission: <code>{run.mission_id}</code>
      </p>

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
