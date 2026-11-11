import type { ReactNode } from 'react'

type Props = {
  // The heading id, so the section is named by its label.
  id: string
  label: string
  children: ReactNode
}

// One phase of a run, told in the order the stream tells it: Question, Splitting
// the dispute, Rules found, Verdict. Each mounts when its event lands and fades
// in, rising to rest; under reduced motion it only fades. Its label is the
// secondary gold, which means a phase and nothing else on the screen.
export function Phase({ id, label, children }: Props) {
  return (
    <section className="phase" aria-labelledby={id}>
      <h2 id={id} className="phase__label eyebrow text-label-lg">
        {label}
      </h2>
      {children}
    </section>
  )
}
