// Written by scripts/make_fixture.py from level 3 records; regenerate rather
// than edit. Dev only, for the design sweep, and deleted at its close. Each is a
// ruling the screen draws differently: the ambiguous flag with marker-slipped
// cites, a number with a cite that names no entry, and a sentence. A yes or no
// draws as a number does. The run's other states come from the scenarios, on
// any of the three. No level 3 dev record combines two of these, so one fixture
// cannot stand for them all.
import type { Fixture } from '../types.ts'
import twoWeapon from './two-weapon-bonus-before-attack.json'
import hasteDash from './haste-dash-distance.json'
import hasteLethargy from './haste-concentration-lethargy.json'

// JSON imports widen string literals, so the event and kind tags arrive as
// `string`. The cast is the boundary; the script writes these shapes.
export const fixtures = [twoWeapon, hasteDash, hasteLethargy] as Fixture[]
