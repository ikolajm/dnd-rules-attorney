// What every capture shares: the browser, the pacing, the keyboard moves and
// the timeline each take writes to takes/<name>.timeline.json, beside OBS's recordings.
import { writeFile } from 'node:fs/promises'
import { chromium, type Locator, type Page } from 'playwright'

// Setup

const SCREEN = 'http://localhost:5173'
export const VIEWPORT = { width: 1024, height: 768 }
const COLOR_SCHEME: 'light' | 'dark' = 'dark'

// Pacing, in milliseconds

export const KEY_DELAY = 45
const TAB_DELAY = 220
const FOCUS_HOLD = 600
const OPTION_DELAY = 260
const SCROLL_LIMIT = 2000
export const HOLD = { short: 1200, read: 3000 }

export const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// A take that cannot be used: the screen showed other than the captions say, or
// a control was not where the script expects it.
export class TakeError extends Error {}

export type Mark = (name: string) => void

// Keyboard

function isFocused(locator: Locator): Promise<boolean> {
  return locator.evaluate((el) => el === document.activeElement)
}

// Tabs until the locator holds focus, so the camera sees each stop on the way.
export async function tabTo(page: Page, locator: Locator, max = 40) {
  for (let i = 0; i < max; i++) {
    if (await isFocused(locator)) return
    await page.keyboard.press('Tab')
    await pause(TAB_DELAY)
  }
  throw new TakeError(`Tab did not reach ${locator}.`)
}

// Focuses the control straight off, past every stop between.
export async function focusOn(locator: Locator) {
  await locator.focus()
  if (!(await isFocused(locator))) throw new TakeError(`${locator} did not take focus.`)
  await pause(FOCUS_HOLD)
}

// Scrolls the page smoothly until the control sits mid-screen, clear of both
// sticky bars, then focuses it where it stands.
export async function scrollToFocus(locator: Locator) {
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

// Opens a select, holds on its list, and arrows to the option before picking it.
export async function choose(page: Page, trigger: Locator, option: string, max = 60) {
  await focusOn(trigger)
  await page.keyboard.press('Enter')
  const listbox = page.getByRole('listbox')
  await listbox.waitFor()
  await pause(HOLD.short)
  const highlighted = listbox.locator('[role="option"][data-highlighted]')
  for (let i = 0; i < max; i++) {
    if ((await highlighted.textContent())?.trim() === option) {
      await page.keyboard.press('Enter')
      await listbox.waitFor({ state: 'detached' })
      await pause(HOLD.short)
      return
    }
    await page.keyboard.press('ArrowDown')
    await pause(OPTION_DELAY)
  }
  throw new TakeError(`The list for ${trigger} has no option "${option}".`)
}

// The encyclopedia, from the page load

export async function openEncyclopedia(page: Page) {
  await tabTo(page, page.getByRole('tab', { name: 'Ask' }))
  await page.keyboard.press('ArrowRight')
  await page.getByRole('tab', { name: 'Encyclopedia', selected: true }).waitFor()
  await page.locator('.encyclopedia__table').waitFor()
}

export async function checkCount(page: Page, expected: string) {
  const results = page.locator('.encyclopedia__results')
  try {
    await results.filter({ hasText: expected }).waitFor({ timeout: 5000 })
  } catch {
    throw new TakeError(`The count reads "${(await results.textContent())?.trim()}", not "${expected}".`)
  }
}

// The run

// Loads the screen, hands the take its page and its mark, and writes the
// timeline once the take ends. A take that cannot be used writes none.
export async function capture(name: string, take: (page: Page, mark: Mark) => Promise<void>) {
  const steps: { name: string; ms: number }[] = []
  let start = 0
  const mark: Mark = (step) => steps.push({ name: step, ms: Math.round(performance.now() - start) })

  // An app window: no tab strip or address bar, only the title bar OBS's Client Area drops.
  // '' gives the persistent context a throwaway profile.
  const context = await chromium.launchPersistentContext('', {
    headless: false,
    args: [`--app=${SCREEN}`],
    viewport: VIEWPORT,
    colorScheme: COLOR_SCHEME,
    reducedMotion: 'no-preference',
  })
  try {
    const page = context.pages()[0] ?? (await context.newPage())
    await page.goto(SCREEN)
    start = performance.now()
    mark('load')
    await take(page, mark)
    mark('end')

    const timeline = new URL(`./takes/${name}.timeline.json`, import.meta.url)
    await writeFile(timeline, JSON.stringify({ capture: name, viewport: VIEWPORT, steps }, null, 2) + '\n')
    console.log(`Timeline written: ${steps.length} steps over ${steps.at(-1)?.ms} ms.`)
  } catch (error) {
    if (!(error instanceof TakeError)) throw error
    console.error(`Take not usable: ${error.message}`)
    process.exitCode = 1
  } finally {
    await context.close()
  }
}
