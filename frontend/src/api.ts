export type Project = {
  id: string
  name: string
  description: string | null
  base_url: string
  created_at: string
}

export type Environment = {
  id: string
  project_id: string
  name: string
  env_type: string
  base_url: string
  safety_level: string
  allow_destructive: boolean
  created_at: string
}

export type Credential = {
  id: string
  project_id: string
  name: string
  auth_type: string
  username: string | null
  login_url: string | null
  has_password: boolean
  has_token: boolean
  has_cookies: boolean
  created_at: string
}

export type Mission = {
  id: string
  project_id: string
  environment_id: string | null
  credential_id: string | null
  title: string
  mission_text: string
  status: string
  created_at: string
}

export type TestStep = {
  id: string
  title: string
  status: string
  detail: string | null
  order_index: number
}

export type Bug = {
  id: string
  title: string
  severity: string
  category: string
  url: string | null
  reproduction_steps: string[]
  expected_result: string | null
  actual_result: string | null
  verified: boolean
  created_at: string
}

export type Evidence = {
  id: string
  evidence_type: string
  path: string | null
  url: string | null
}

export type TestRun = {
  id: string
  mission_id: string
  plan_id: string | null
  lifecycle: string
  started_at: string | null
  finished_at: string | null
  summary: Record<string, number> | null
  application_map: { pages?: { url: string; title: string }[] } | null
  report_path: string | null
  is_regression: boolean
  parent_run_id: string | null
  error_message: string | null
  steps: TestStep[]
  bugs: Bug[]
  evidences: Evidence[]
}

export type DashboardStats = {
  projects: number
  missions: number
  runs: number
  tests_total: number
  tests_passed: number
  tests_failed: number
  tests_blocked: number
  bugs_by_severity: Record<string, number>
}

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  dashboard: () => request<DashboardStats>('/dashboard'),
  projects: () => request<Project[]>('/projects'),
  createProject: (body: { name: string; description?: string; base_url: string }) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(body) }),
  environments: (projectId: string) =>
    request<Environment[]>(`/projects/${projectId}/environments`),
  createEnvironment: (
    projectId: string,
    body: {
      name: string
      env_type: string
      base_url: string
      safety_level: string
      allow_destructive?: boolean
    },
  ) =>
    request<Environment>(`/projects/${projectId}/environments`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  credentials: (projectId: string) =>
    request<Credential[]>(`/projects/${projectId}/credentials`),
  createCredential: (
    projectId: string,
    body: {
      name: string
      auth_type: string
      username?: string
      password?: string
      login_url?: string
    },
  ) =>
    request<Credential>(`/projects/${projectId}/credentials`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  missions: (projectId: string) => request<Mission[]>(`/projects/${projectId}/missions`),
  createMission: (
    projectId: string,
    body: {
      title: string
      mission_text: string
      environment_id?: string
      credential_id?: string
    },
  ) =>
    request<Mission>(`/projects/${projectId}/missions`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  startMission: (missionId: string) =>
    request<{ status: string }>(`/missions/${missionId}/start`, { method: 'POST' }),
  runs: (missionId: string) => request<TestRun[]>(`/missions/${missionId}/runs`),
  run: (runId: string) => request<TestRun>(`/runs/${runId}`),
  retest: (runId: string) =>
    request<{ status: string }>(`/runs/${runId}/retest`, { method: 'POST' }),
  bugs: (projectId: string) => request<Bug[]>(`/projects/${projectId}/bugs`),
  query: (body: { question: string; run_id?: string; project_id?: string }) =>
    request<{ answer: string; sources: string[] }>('/query', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
