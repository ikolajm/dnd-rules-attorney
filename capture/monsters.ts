// The monsters capture: the encyclopedia narrowed to dragons, sorted by
// challenge, and one dragon's stat block opened, by keyboard.
//
//   node monsters.ts
//
// Needs the screen running; the encyclopedia reads the data files in the browser.
import type { Page } from 'playwright'
import { capture, checkCount, choose, focusOn, HOLD, openEncyclopedia, pause, scrollToFocus, type Mark } from './take.ts'

async function take(page: Page, mark: Mark) {
  await pause(HOLD.short)
  await openEncyclopedia(page)
  await pause(HOLD.short)

  mark('kind')
  await choose(page, page.getByLabel('Kind', { exact: true }), 'Monsters')
  await checkCount(page, '334 of 334')

  await focusOn(page.getByRole('button', { name: 'Filters' }))
  mark('filters')
  await page.keyboard.press('Enter')
  await pause(HOLD.short)

  mark('type')
  await choose(page, page.getByLabel('Type', { exact: true }), 'Dragon')
  await checkCount(page, '43 of 334')

  // Twice: the first press sorts ascending, the second descending.
  await focusOn(page.locator('thead').getByRole('button', { name: 'Challenge', exact: true }))
  mark('sort')
  await page.keyboard.press('Enter')
  await pause(HOLD.short)
  await page.keyboard.press('Enter')
  await pause(HOLD.short)

  await scrollToFocus(page.locator('.encyclopedia__table').getByRole('button', { name: 'Ancient Red Dragon' }))
  mark('open')
  await page.keyboard.press('Enter')
  await page.locator('#source-title').filter({ hasText: 'Ancient Red Dragon' }).waitFor()
  await pause(HOLD.read)
}

await capture('monsters', take)
