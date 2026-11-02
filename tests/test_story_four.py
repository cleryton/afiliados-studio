from datetime import datetime
import json
import unittest
from unittest.mock import patch
import core
import story_director
import story_week
from story_week_catalog import STORIES,FOUR_NUMBERS,caption
from tests import test_story_expansion as fixtures


class FourPerDayTests(unittest.TestCase):
    slots=fixtures.ExpansionTests.slots

    def setUp(self):
        fixtures.ExpansionTests.setUp(self)
        story_week.expand({'id':self.week})
        with core.db() as c:
            c.execute('UPDATE story_weeks SET enabled=0')
            c.execute("UPDATE story_week_slots SET status='ready'")

    def expand(self):return story_week.expand_four({'id':self.week})

    def test_adds_seven_future_slots_preserving_all_twenty_one_records(self):
        before={r['id']:r for r in self.slots()};result=self.expand();rows=self.slots()
        self.assertEqual(result['added'],7);self.assertEqual(len(rows),28)
        self.assertEqual({r['id']:r for r in rows if r['number']<30},before)
        for day in range(2,9):
            group=[r for r in rows if r['due_at'].startswith(f'2026-11-{day:02d}')]
            self.assertEqual([r['due_at'][11:16] for r in group],['12:00','15:00','18:00','21:00'])
        new=[r for r in rows if r['number'] in FOUR_NUMBERS]
        self.assertTrue(all(r['status']=='queued' and not r['media_id'] for r in new))
        self.assertTrue(all(json.loads(r['creative_plan'])['report']['status']=='script_checked' for r in new))

    def test_repeat_preserves_a_pause_and_partial_expansion_requires_review(self):
        self.expand()
        with core.db() as c:c.execute('UPDATE story_weeks SET paused=1,enabled=0')
        self.assertTrue(self.expand()['existing']);self.assertEqual(len(self.slots()),28)
        with core.db() as c:
            self.assertEqual(c.execute('SELECT paused FROM story_weeks').fetchone()[0],1)
            c.execute('DELETE FROM story_week_slots WHERE number=36')
        with self.assertRaises(ValueError):self.expand()
        self.assertEqual(len(self.slots()),27)

    def test_unavailable_or_overdue_expansion_never_partially_inserts(self):
        changes=(patch.object(core,'now',return_value=datetime(2026,11,2,15,tzinfo=core.TZ)),
                 patch('story_offers.current',return_value=False),patch('story_week.capacity',return_value=False),
                 patch('story_native.blocks_api',return_value=True))
        for change in changes:
            with change,self.assertRaises(ValueError):self.expand()
            self.assertEqual(len(self.slots()),21)
        with core.db() as c:c.execute("UPDATE story_week_slots SET due_at='2026-11-02T15:00:00-03:00' WHERE number=9")
        with self.assertRaises(ValueError):self.expand()
        self.assertEqual(len(self.slots()),21)

    def test_scripts_have_distinct_content_and_preserve_the_offer(self):
        used={s['text'] for n in range(9,30) for s in STORIES[n]['scenes']}
        for number in FOUR_NUMBERS:
            story,report=story_director.plan(STORIES[number]);texts={s['text'] for s in story['scenes']}
            self.assertFalse(texts&used);used.update(texts);self.assertTrue(report['standalone_payoff'])
            value=caption(number,self.offer,story)
            self.assertIn('Mistérios da vizinhança',value);self.assertIn(self.offer['url'],value)
            self.assertLessEqual(len(' '.join(value.split())),2200)


if __name__=='__main__':unittest.main()
