from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import core
import stories
import story_week
import story_director
from story_week_catalog import STORIES, EXTRA_NUMBERS, caption


class ExpansionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        data=patch.object(core,'DATA',Path(temporary.name));data.start();self.addCleanup(data.stop)
        clock=patch.object(core,'now',return_value=datetime(2026,11,1,12,tzinfo=core.TZ));clock.start();self.addCleanup(clock.stop)
        core.init();stories.create_pilot();stories.set_profile({'handle':'fiction_project'})
        self.offer={'name':'Fixture','url':'https://example.com/own','facts':['Fixture fact.'],'product_hash':'f'*64}
        for mock in (patch('story_offers.for_series',return_value=self.offer),patch('story_offers.current',return_value=True),
                     patch('story_week.capacity',return_value=True)):
            mock.start();self.addCleanup(mock.stop)
        self.week=story_week.prepare({'start_date':'2026-11-02','collection':'standalone'})['id']
        with core.db() as c:
            c.execute('UPDATE story_weeks SET enabled=0')
            c.execute("UPDATE story_week_slots SET status='ready'")

    def slots(self):
        with core.db() as c:return [dict(r) for r in c.execute('SELECT * FROM story_week_slots ORDER BY due_at')]

    def expand(self):return story_week.expand({'id':self.week})

    def test_adds_fourteen_original_slots_preserving_every_original_field(self):
        before={r['id']:r for r in self.slots()};result=self.expand();rows=self.slots()
        self.assertEqual(result['added'],14);self.assertEqual(len(rows),21)
        self.assertEqual({r['id']:r for r in rows if r['number']<16},before)
        for day in range(2,9):
            group=[r for r in rows if r['due_at'].startswith(f'2026-11-{day:02d}')]
            self.assertEqual([r['due_at'][11:16] for r in group],['12:00','18:00','21:00'])
        self.assertTrue(all(json.loads(r['creative_plan'])['report']['status']=='script_checked' for r in rows if r['number']>=16))
        self.assertTrue(all(not r['media_id'] and r['status']=='queued' for r in rows if r['number']>=16))

    def test_repeat_and_restart_do_not_add_copies_or_resume_a_pause(self):
        self.expand()
        with core.db() as c:c.execute('UPDATE story_weeks SET paused=1,enabled=0')
        story_week.init();again=self.expand()
        self.assertTrue(again['existing']);self.assertEqual(again['added'],0);self.assertEqual(len(self.slots()),21)
        with core.db() as c:self.assertEqual(c.execute('SELECT paused FROM story_weeks').fetchone()[0],1)

    def test_paused_incomplete_or_active_production_cannot_be_expanded(self):
        for change in ("UPDATE story_weeks SET paused=1", "UPDATE story_week_slots SET status='queued' WHERE number=9", "UPDATE story_weeks SET enabled=1"):
            with self.subTest(change=change):
                with core.db() as c:c.execute(change)
                with self.assertRaises(ValueError):self.expand()
                self.assertEqual(len(self.slots()),7)
                with core.db() as c:
                    c.execute('UPDATE story_weeks SET paused=0,enabled=0');c.execute("UPDATE story_week_slots SET status='ready'")

    def test_wrong_week_profile_revoked_offer_or_capacity_do_not_mutate(self):
        with self.assertRaises(ValueError):story_week.expand({'id':'f'*32})
        stories.set_profile({'handle':'another_project'})
        with self.assertRaises(ValueError):self.expand()
        stories.set_profile({'handle':'fiction_project'})
        for mock in (patch('story_offers.current',return_value=False),patch('story_week.capacity',return_value=False)):
            with mock,self.assertRaises(ValueError):self.expand()
        self.assertEqual(len(self.slots()),7)

    def test_past_extra_slot_is_held_instead_of_shifted_or_published_now(self):
        with patch.object(core,'now',return_value=datetime(2026,11,2,13,tzinfo=core.TZ)),self.assertRaises(ValueError):self.expand()
        self.assertEqual(len(self.slots()),7)

    def test_conflicting_hour_prevents_partial_insertion(self):
        with core.db() as c:c.execute("UPDATE story_week_slots SET due_at='2026-11-02T12:00:00-03:00' WHERE number=9")
        with self.assertRaises(ValueError):self.expand()
        self.assertEqual(len(self.slots()),7)

    def test_partial_existing_expansion_requires_review(self):
        self.expand()
        with core.db() as c:c.execute('DELETE FROM story_week_slots WHERE number=29')
        with self.assertRaises(ValueError):self.expand()
        self.assertEqual(len(self.slots()),20)

    def test_external_record_for_extra_story_prevents_duplicate_creation(self):
        with patch('story_library.native_post_exists',side_effect=lambda key,handle:key.endswith(':16')):
            with self.assertRaises(ValueError):self.expand()
        self.assertEqual(len(self.slots()),7)

    def test_every_new_script_is_distinct_complete_and_caption_preserves_authorized_offer(self):
        old={s['text'] for n in range(9,16) for s in STORIES[n]['scenes']}
        used=set()
        for number in EXTRA_NUMBERS:
            story,report=story_director.plan(STORIES[number]);text=tuple(s['text'] for s in story['scenes'])
            self.assertEqual(report['issues'],[]);self.assertTrue(report['standalone_payoff'])
            self.assertFalse(set(text)&old);self.assertFalse(set(text)&used);used.update(text)
            value=caption(number,self.offer,story)
            self.assertIn('de 14:',value);self.assertIn(self.offer['url'],value);self.assertIn('PUBLICIDADE',value)
            self.assertLessEqual(len(' '.join(value.split())),2200)


if __name__=='__main__':unittest.main()
