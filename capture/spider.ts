// The spider capture: one question asked and two of its citations opened, by
// keyboard.
//
//   node spider.ts
//
// Needs the server and the screen running, as the readme sets out.
import type { Page } from 'playwright'
import { capture, focusOn, HOLD, KEY_DELAY, pause, scrollToFocus, tabTo, TakeError, type Mark } from './take.ts'

const QUESTION = 'My 4th-level druid wants to Wild Shape into a giant spider. Can she?'
const RUN_LIMIT = 180_000

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

async function take(page: Page, mark: Mark) {
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
}

await capture('spider', take)
