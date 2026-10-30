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

// The stage a run failed at, as the screen names it. The server sends the
// first three; the frontend alone sets server-unreachable, for a server it
// could not reach or that stopped before the run ended.
export type ErrorReason = 'unreachable' | 'ruling-unparsed' | 'timeout' | 'server-unreachable'

// The gate's data mirrors `Gate` in rules_attorney.gate, and the error's the
// events rules_attorney.stream yields.
export type StreamEvent =
  | { event: 'gate'; data: { about_rules: boolean } }
  | { event: 'plan'; data: { sub_questions: string[] } }
  | { event: 'entries'; data: { entries: Entry[] } }
  | { event: 'ruling'; data: Ruling }
  | { event: 'error'; data: { reason: ErrorReason } }
