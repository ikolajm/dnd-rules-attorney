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

export const STAGE_LABEL: Record<Run['stage'], string> = {
  checking: 'Checking the question',
  splitting: 'Splitting the dispute',
  finding: 'Finding the rules',
  ruling: 'Ruling',
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
