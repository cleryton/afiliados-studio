from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import core
import story_followup


class FollowupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        data = patch.object(core, 'DATA', Path(temporary.name)); data.start(); self.addCleanup(data.stop)
        self.now = datetime(2026, 11, 1, 15, tzinfo=core.TZ)
        clock = patch.object(core, 'now', return_value=self.now); clock.start(); self.addCleanup(clock.stop)
        self.week = {'id': 'fixture-week', 'handle': 'fiction_project', 'slots': [{}, {}], 'native_registered': 1}
        self.path = core.DATA / 'story-week' / 'automation-status.json'
        self.path.parent.mkdir()

    def write(self, **changes):
        value = {'week_id': self.week['id'], 'observed_at': self.now.isoformat(), 'status': 'login_required', **changes}
        self.path.write_text(json.dumps(value), encoding='utf-8')

    def state(self):
        return story_followup.state(self.week, 'fiction_project')

    def test_absent_or_unrelated_observation_does_not_claim_current_status(self):
        self.assertIsNone(self.state())
        self.write(week_id='old-week'); self.assertIsNone(self.state())
        self.write(); self.assertIsNone(story_followup.state(self.week, 'another_project'))
        self.assertIsNone(story_followup.state(None, 'fiction_project'))

    def test_login_observation_is_bounded_and_does_not_expose_arbitrary_fields(self):
        self.write(confirmed=999, error='PRIVATE_FIXTURE', api_key='PRIVATE_FIXTURE', message='PRIVATE_FIXTURE')
        result = self.state()
        self.assertEqual(result['code'], 'login_required'); self.assertFalse(result['stale'])
        self.assertNotIn('PRIVATE_FIXTURE', json.dumps(result)); self.assertNotIn('confirmed', result)

    def test_old_observation_requires_recheck_instead_of_claiming_current_login(self):
        self.write(observed_at=(self.now - timedelta(hours=13)).isoformat())
        result = self.state(); self.assertTrue(result['stale'])
        self.assertIn('12 horas', result['message']); self.assertNotIn('encontrou a tela', result['message'])

    def test_malformed_oversized_or_unknown_records_do_not_break_dashboard(self):
        for raw in ('{', '[]', '[' * 1500 + ']' * 1500, 'x' * 8193,
                    json.dumps({'status': 'PRIVATE_FIXTURE', 'week_id': self.week['id']})):
            with self.subTest(raw=raw[:30]):
                self.path.write_text(raw, encoding='utf-8')
                result = self.state(); self.assertEqual(result['code'], 'unavailable')
                self.assertNotIn('PRIVATE_FIXTURE', result['message'])

    def test_invalid_naive_or_future_dates_cannot_be_treated_as_fresh(self):
        for date in (None, [], 'invalid', '2026-11-01T15:00:00', (self.now + timedelta(hours=1)).isoformat()):
            with self.subTest(date=date):
                self.write(observed_at=date); self.assertEqual(self.state()['code'], 'unavailable')

    def test_receipts_override_old_login_and_never_claim_effective_publication(self):
        self.write(); self.week['native_registered'] = 2
        result = self.state(); self.assertEqual(result['code'], 'complete')
        self.assertIn('publicação efetiva ainda precisa', result['message'])

    def test_summary_completion_cannot_override_missing_receipts(self):
        self.write(status='complete', confirmed=2)
        result = self.state()
        self.assertNotIn('Todos os capítulos', result['message'])
        self.assertEqual(self.week['native_registered'], 1)

    def test_directory_read_failure_is_reported_without_crashing(self):
        self.path.mkdir()
        self.assertEqual(self.state()['code'], 'unavailable')


if __name__ == '__main__': unittest.main()
