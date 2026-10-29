// Written by scripts/make_fixture.py from level 3 records; regenerate rather
// than edit. Between them they cover each state the finished screen has: a yes,
// the ambiguous flag with marker-slipped cites, a number, a sentence, and a cite
// that names no entry.
import type { Fixture } from '../types.ts'
import grappled from './grappled-attack-and-cast.json'
import twoWeapon from './two-weapon-bonus-before-attack.json'
import hasteDash from './haste-dash-distance.json'
import hasteLethargy from './haste-concentration-lethargy.json'
import sleepTempHp from './sleep-temp-hp.json'

// JSON imports widen string literals, so the event and kind tags arrive as
// `string`. The cast is the boundary; the script writes these shapes.
export const fixtures = [grappled, twoWeapon, hasteDash, hasteLethargy, sleepTempHp] as Fixture[]
