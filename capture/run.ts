// The spider capture: one question asked and two of its citations opened, by
// keyboard, each step written to timeline.json with its time from the page load.
//
//   node run.ts
//
// Needs the server and the screen running, as the readme sets out.
import { writeFile } from 'node:fs/promises'
import { chromium, type Locator, type Page } from 'playwright'

// Setup

const SCREEN = 'http://localhost:5173'
const QUESTION = 'My 4th-level druid wants to Wild Shape into a giant spider. Can she?'
const VIEWPORT = { width: 1600, height: 900 }
const COLOR_SCHEME: 'light' | 'dark' = 'dark'
const TIMELINE = new URL('./timeline.json', import.meta.url)

// Pacing, in milliseconds

const KEY_DELAY = 45
const TAB_DELAY = 220
const FOCUS_HOLD = 600
const SCROLL_LIMIT = 2000
const HOLD = { short: 1200, read: 3000 }
const RUN_LIMIT = 180_000

// Timeline

type Step = { name: string; ms: number }

const steps: Step[] = []
let start = 0

function mark(name: string) {
  steps.push({ name, ms: Math.round(performance.now() - start) })
}

const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// A take that cannot be used: the run ruled or cited otherwise, or a control
// was not where the script expects it.
class TakeError extends Error {}

// Keyboard

function isFocused(locator: Locator): Promise<boolean> {
  return locator.evaluate((el) => el === document.activeElement)
}

// Tabs until the locator holds focus, so the camera sees each stop on the way.
async function tabTo(page: Page, locator: Locator, max = 40) {
  for (let i = 0; i < max; i++) {
    if (await isFocused(locator)) return
    await page.keyboard.press('Tab')
    await pause(TAB_DELAY)
  }
  throw new TakeError(`Tab did not reach ${locator}.`)
}

// Focuses the control straight off, past every stop between.
async function focusOn(locator: Locator) {
  await locator.focus()
  if (!(await isFocused(locator))) throw new TakeError(`${locator} did not take focus.`)
  await pause(FOCUS_HOLD)
}

// Scrolls the page smoothly until the control sits mid-screen, clear of both
// sticky bars, then focuses it where it stands.
async function scrollToFocus(locator: Locator) {
  await locator.evaluate(
    (el, limit) =>
      new Promise<void>((resolve) => {
        const done = () => resolve()
        window.addEventListener('scrollend', done, { once: true })
        // No scrollend fires when the control is already mid-screen.
        setTimeout(done, limit)
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }),
    SCROLL_LIMIT,
  )
  await locator.evaluate((el) => (el as HTMLElement).focus({ preventScroll: true }))
  if (!(await isFocused(locator))) throw new TakeError(`${locator} did not take focus.`)
  await pause(FOCUS_HOLD)
}

// The ruling the captions describe

async function checkRuling(page: Page) {
  const answer = (await page.locator('.verdict__answer').textContent())?.trim()
  if (answer !== 'No') throw new TakeError(`The verdict is "${answer}", not "No".`)

  const summary = (await page.locator('.view-all__summary').textContent())?.trim()
  if (summary !== '10 entries retrieved, 2 cited') {
    throw new TakeError(`The summary reads "${summary}", not "10 entries retrieved, 2 cited".`)
  }

  const cites = (await page.locator('.verdict__cite-list button').allTextContents()).map((t) => t.trim())
  if (cites.length !== 2 || !cites.includes('Wild Shape') || !cites.includes('Giant Spider')) {
    throw new TakeError(`The ruling cites ${JSON.stringify(cites)}, not Wild Shape and Giant Spider.`)
  }
}

// The take

async function take(page: Page) {
  await page.goto(SCREEN)
  start = performance.now()
  mark('load')
  await pause(HOLD.read)

  await tabTo(page, page.getByLabel('Rules question'))
  mark('type')
  await page.keyboard.type(QUESTION, { delay: KEY_DELAY })
  await pause(HOLD.short)

  mark('submit')
  await page.keyboard.press('Enter')
  // The Verdict phase mounts whether the run ruled or ended without a ruling.
  await page.locator('#phase-verdict').waitFor({ timeout: RUN_LIMIT })
  const status = page.locator('.phase:has(#phase-verdict) .status')
  if (await status.count()) {
    throw new TakeError(`The run ended without a ruling: ${(await status.innerText()).replace(/\s+/g, ' ')}`)
  }
  mark('verdict')
  await checkRuling(page)
  await pause(HOLD.read)

  await scrollToFocus(page.locator('.view-all__summary'))
  mark('retrieved')
  await page.keyboard.press('Enter')
  await pause(HOLD.read)

  const panel = page.locator('.source-panel')
  const panelTitle = page.locator('#source-title')

  await scrollToFocus(page.locator('.view-all__list button', { hasText: 'Wild Shape' }))
  mark('cite-list')
  await page.keyboard.press('Enter')
  await panelTitle.filter({ hasText: 'Wild Shape' }).waitFor()
  await pause(HOLD.read)

  mark('close')
  await page.keyboard.press('Escape')
  await panel.waitFor({ state: 'detached' })
  await pause(HOLD.short)

  await scrollToFocus(page.locator('.verdict__cite-list').getByRole('button', { name: 'Giant Spider' }))
  mark('cite-button')
  await page.keyboard.press('Enter')
  await panelTitle.filter({ hasText: 'Giant Spider' }).waitFor()
  await pause(HOLD.short)

  await focusOn(panel.getByRole('tab', { name: 'Formatted' }))
  mark('source-text')
  await page.keyboard.press('ArrowRight')
  await panel.getByRole('tab', { name: 'Source text', selected: true }).waitFor()
  await panel.getByText('Challenge: 1').waitFor()
  await pause(HOLD.read)

  mark('formatted')
  await page.keyboard.press('ArrowLeft')
  await panel.getByRole('tab', { name: 'Formatted', selected: true }).waitFor()
  await pause(HOLD.read)
  mark('end')
}

const browser = await chromium.launch({ headless: false })
try {
  const context = await browser.newContext({
    viewport: VIEWPORT,
    colorScheme: COLOR_SCHEME,
    reducedMotion: 'no-preference',
  })
  await take(await context.newPage())
  await writeFile(TIMELINE, JSON.stringify({ question: QUESTION, viewport: VIEWPORT, steps }, null, 2) + '\n')
  console.log(`Timeline written: ${steps.length} steps over ${steps.at(-1)?.ms} ms.`)
} catch (error) {
  if (!(error instanceof TakeError)) throw error
  console.error(`Take not usable: ${error.message}`)
  process.exitCode = 1
} finally {
  await browser.close()
}
