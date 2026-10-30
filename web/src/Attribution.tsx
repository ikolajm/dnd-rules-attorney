import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/loom/dialog.tsx'

// The SRD 5.1 credit: one line at the foot, kept visible, since CC-BY asks for
// attribution in a reasonable manner, opening the full statement. It is the
// wording Wizards of the Coast gives for SRD 5.1 with the document's and the
// licence's names linked in place of their URLs written out, which CC-BY 4.0
// accepts; the README carries the statement word for word.
export function Attribution() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button type="button" className="link link-prose">
          SRD 5.1 · CC-BY-4.0
        </button>
      </DialogTrigger>
      <DialogContent size="sm">
        <DialogHeader showClose>
          <DialogTitle>Rules text</DialogTitle>
        </DialogHeader>
        <DialogDescription>
          This work includes material taken from the{' '}
          <a className="link link-prose" href="https://dnd.wizards.com/resources/systems-reference-document">
            System Reference Document 5.1 (“SRD 5.1”)
          </a>{' '}
          by Wizards of the Coast LLC. The SRD 5.1 is licensed under the{' '}
          <a className="link link-prose" href="https://creativecommons.org/licenses/by/4.0/legalcode">
            Creative Commons Attribution 4.0 International License
          </a>
          .
        </DialogDescription>
      </DialogContent>
    </Dialog>
  )
}
