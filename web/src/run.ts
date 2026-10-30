import type { Entry, ErrorReason, Ruling, StreamEvent } from './types.ts'

// One question's run, built up event by event. Each region shows nothing until
// its event arrives, and whatever arrived stays when the run ends early.

export type Phase = 'running' | 'ruled' | 'refused' | 'error' | 'stopped'

export type Run = {
  question: string
  phase: Phase
  // The last stage reached, which names the wait while the run is open.
  stage: 'checking' | 'splitting' | 'finding' | 'ruling'
  subQuestions: string[] | null
  entries: Entry[] | null
  ruling: Ruling | null
  error: ErrorReason | null
}

// The phases, in the order a run reaches them, each named as its label reads.
export const PHASE_LABEL = {
  question: 'Question',
  plan: 'Splitting the dispute',
  entries: 'Rules found',
  verdict: 'Verdict',
} as const

// While a run waits, the label of the phase it is waiting on, shown pending at
// the foot. Before the gate answers, the dispute is next to be split.
export const PENDING_LABEL: Record<Run['stage'], string> = {
  checking: PHASE_LABEL.plan,
  splitting: PHASE_LABEL.plan,
  finding: PHASE_LABEL.entries,
  ruling: PHASE_LABEL.verdict,
}

export function startRun(question: string): Run {
  return {
    question,
    phase: 'running',
    stage: 'checking',
    subQuestions: null,
    entries: null,
    ruling: null,
    error: null,
  }
}

export function applyEvent(run: Run, e: StreamEvent): Run {
  switch (e.event) {
    case 'gate':
      return e.data.about_rules ?{ ...run, stage: 'splitting' } : { ...run, phase: 'refused' }
    case 'plan':
      return { ...run, stage: 'finding', subQuestions: e.data.sub_questions }
    case 'entries':
      return { ...run, stage: 'ruling', entries: e.data.entries }
    case 'ruling':
      return { ...run, phase: 'ruled', ruling: e.data }
    case 'error':
      return { ...run, phase: 'error', error: e.data.reason }
  }
}
