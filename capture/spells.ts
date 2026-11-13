// The spells capture: the encyclopedia's spells narrowed to 3rd-level
// evocation, and Fireball opened, by keyboard.
//
//   node spells.ts
//
// Needs the screen running; the encyclopedia reads the data files in the browser.
import type { Page } from 'playwright'
import { capture, checkCount, choose, focusOn, HOLD, openEncyclopedia, pause, scrollToFocus, type Mark } from './take.ts'

async function take(page: Page, mark: Mark) {
  await pause(HOLD.short)
  await openEncyclopedia(page)
  await checkCount(page, '319 of 319')
  await pause(HOLD.short)

  await focusOn(page.getByRole('button', { name: 'Filters' }))
  mark('filters')
  await page.keyboard.press('Enter')
  await pause(HOLD.short)

  mark('school')
  await choose(page, page.getByLabel('School', { exact: true }), 'Evocation')

  mark('level')
  await choose(page, page.getByLabel('Level', { exact: true }), '3')
  await checkCount(page, '7 of 319')

  await scrollToFocus(page.locator('.encyclopedia__table').getByRole('button', { name: 'Fireball' }))
  mark('open')
  await page.keyboard.press('Enter')
  await page.locator('#source-title').filter({ hasText: 'Fireball' }).waitFor()
  await pause(HOLD.read)
}

await capture('spells', take)
