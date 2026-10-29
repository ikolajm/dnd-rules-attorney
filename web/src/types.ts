// The shapes the endpoint sends, mirrored from the Python models: `Ruling` and
// its answer kinds in rules_attorney.answer, the sub-questions in
// rules_attorney.multihop. A change there is a change here.

export type Answer =
  | { kind: 'yes-or-no'; verdict: 'yes' | 'no' }
  | { kind: 'how-many'; verdict: number }
  | { kind: 'what'; verdict: string }

export type Ruling = {
  explanation: string
  ambiguous: boolean
  answer: Answer
  cites: string[]
}

export type Entry = {
  path: string
  text: string
}

// The stage a run failed at, as the screen names it.
export type ErrorReason = 'unreachable' | 'plan-unparsed' | 'ruling-unparsed' | 'timeout'

// The gate's and the error's data are placeholders until the gate call and the
// endpoint are written; they own the real shapes.
export type StreamEvent =
  | { event: 'gate'; data: { allowed: boolean } }
  | { event: 'plan'; data: { sub_questions: string[] } }
  | { event: 'entries'; data: { entries: Entry[] } }
  | { event: 'ruling'; data: Ruling }
  | { event: 'error'; data: { reason: ErrorReason } }

export type Fixture = {
  source: { run: string; id: string; model: string; commit: string; gate: string }
  question: string
  events: StreamEvent[]
}
