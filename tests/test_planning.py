from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import autopilot
import campaigns
import catalog
import content_engine
import core
import planning
import youtube_client as yt


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=patch.object(core,'DATA',Path(self.temp.name));override.start();self.addCleanup(override.stop)
        core.init();autopilot.init();catalog.init();yt.init()
        content_engine.configure({'mode':'rules'})
        self.current=datetime(2026,10,22,16,tzinfo=core.TZ)
        clock=patch('core.now',return_value=self.current);clock.start();self.addCleanup(clock.stop)
        autopilot.configure({'enabled':True,'daily_limit':2,'hours':[18,20]})

    def job(self,index=0,status='ready',due=None,automatic=True):
        pid=core.save_product({'name':f'Organizador {index}','url':f'https://example.com/{index}?af=original',
             'kind':'physical','category':'Casa','description':'Possui três divisórias. Estrutura em madeira.'})
        autopilot.approve_product(pid,{'active':True,'approved':True})
        jid=core.create_job({'product_id':pid})
        with core.db() as c:
            c.execute('UPDATE jobs SET status=?,rights=1,due_at=? WHERE id=?',(status,(due or self.current-timedelta(days=1)).isoformat(),jid))
            if automatic:c.execute('INSERT INTO auto_jobs(job_id,variant) VALUES (?,0)',(jid,))
        return pid,jid

    def remote(self,jid,stage='processing',video='abc12345678'):
        with core.db() as c:c.execute('INSERT INTO youtube_jobs(job_id,stage,video_id,updated_at) VALUES (?,?,?,?)',(jid,stage,video,core.stamp()))

    def test_offline_catchup_keeps_order_and_future_reservations(self):
        _,first=self.job(0,due=self.current.replace(hour=10))
        _,second=self.job(1,due=self.current.replace(hour=12))
        _,future=self.job(2,due=self.current.replace(hour=20))
        self.assertEqual(planning.recover_overdue(),[first,second])
        self.assertEqual(datetime.fromisoformat(core.get_job(first)['due_at']),self.current.replace(hour=18))
        self.assertEqual(datetime.fromisoformat(core.get_job(second)['due_at']),(self.current+timedelta(days=1)).replace(hour=18))
        self.assertEqual(datetime.fromisoformat(core.get_job(future)['due_at']),self.current.replace(hour=20))
        self.assertEqual(planning.recover_overdue(),[])

    def test_actual_publication_day_consumes_daily_limit(self):
        _,published=self.job(status='published')
        with core.db() as c:c.execute('UPDATE jobs SET published_at=? WHERE id=?',(self.current.replace(hour=11).isoformat(),published))
        autopilot.put_settings({'daily_limit':1})
        slot=autopilot.next_slot(autopilot.settings(),self.current)
        self.assertEqual(slot.date(),(self.current+timedelta(days=1)).date())

    def test_future_old_reservation_does_not_consume_day_after_real_publication(self):
        _,jid=self.job(status='published',due=self.current+timedelta(days=2))
        with core.db() as c:c.execute('UPDATE jobs SET published_at=? WHERE id=?',((self.current-timedelta(days=2)).isoformat(),jid))
        self.assertEqual(autopilot.next_slot(autopilot.settings(),self.current),self.current.replace(hour=18))

    def test_dates_are_normalized_to_brasilia_including_midnight(self):
        _,jid=self.job(status='published')
        # 01:00 UTC is still the previous date in Brasília.
        with core.db() as c:c.execute('UPDATE jobs SET published_at=? WHERE id=?',('2026-10-23T01:00:00+00:00',jid))
        autopilot.put_settings({'daily_limit':1})
        self.assertEqual(autopilot.next_slot(autopilot.settings(),self.current).date(),(self.current+timedelta(days=1)).date())

    def test_missed_local_slots_no_longer_occupy_today(self):
        for i,hour in enumerate((8,10,12)):self.job(i,due=self.current.replace(hour=hour))
        self.assertEqual(autopilot.next_slot(autopilot.settings(),self.current),self.current.replace(hour=18))

    def test_unconfirmed_external_schedule_still_reserves_its_day(self):
        _,jid=self.job(due=self.current.replace(hour=12));self.remote(jid,'scheduled')
        autopilot.put_settings({'daily_limit':1})
        self.assertEqual(autopilot.next_slot(autopilot.settings(),self.current).date(),(self.current+timedelta(days=1)).date())
        before=core.get_job(jid)['due_at'];self.assertEqual(planning.recover_overdue(),[])
        self.assertEqual(core.get_job(jid)['due_at'],before)

    def test_global_product_campaign_catalog_and_rights_pause_are_preserved(self):
        pid,jid=self.job();before=core.get_job(jid)['due_at']
        for reason in ('global','product','campaign','catalog','rights'):
            with self.subTest(reason=reason):
                if reason=='global':autopilot.put_settings({'enabled':False})
                if reason=='product':autopilot.approve_product(pid,{'active':False,'approved':True})
                if reason=='campaign':campaigns.save({'name':'Mesa','active':False,'product_ids':[pid]})
                if reason=='catalog':
                    with core.db() as c:c.execute('INSERT INTO catalog_items VALUES (?,?,0,?)',('sku',pid,core.stamp()))
                if reason=='rights':
                    with core.db() as c:c.execute('UPDATE jobs SET rights=0 WHERE id=?',(jid,))
                self.assertIsNone(planning.reserve_late(jid));self.assertEqual(core.get_job(jid)['due_at'],before)
                autopilot.put_settings({'enabled':True});autopilot.approve_product(pid,{'active':True,'approved':True})
                with core.db() as c:
                    c.execute('UPDATE campaigns SET active=1');c.execute('DELETE FROM catalog_items');c.execute('UPDATE jobs SET rights=1 WHERE id=?',(jid,))

    def test_manual_rendering_and_error_jobs_are_not_rescheduled(self):
        for index,(status,automatic) in enumerate([('queued',False),('rendering',True),('error',True),('draft',True)]):
            _,jid=self.job(index,status=status,automatic=automatic)
            self.assertIsNone(planning.reserve_late(jid))
        self.assertEqual(planning.recover_overdue(),[])

    def test_remote_attempts_and_buffer_claims_never_move_locally(self):
        for index,stage in enumerate(('initializing','uploading','processing','scheduled','held','uncertain','failed')):
            _,jid=self.job(index);self.remote(jid,stage)
            self.assertIsNone(planning.reserve_late(jid))
        _,jid=self.job(8)
        with core.db() as c:c.execute("UPDATE auto_jobs SET delivery='sending' WHERE job_id=?",(jid,))
        self.assertIsNone(planning.reserve_late(jid))
        with core.db() as c:c.execute("UPDATE auto_jobs SET delivery='local',buffer_id='existing' WHERE job_id=?",(jid,))
        self.assertIsNone(planning.reserve_late(jid))

    def test_local_hold_can_move_but_processing_needs_confirmed_id(self):
        _,held=self.job();self.remote(held,'held_local','')
        self.assertEqual(planning.reserve_late(held),self.current.replace(hour=18))
        _,processing=self.job(1);self.remote(processing,'processing','')
        self.assertIsNone(planning.reserve_late(processing,processing=True))

    def test_private_processing_reserves_without_double_counting_itself(self):
        autopilot.put_settings({'daily_limit':1})
        _,jid=self.job(due=self.current.replace(hour=12));self.remote(jid)
        self.assertEqual(planning.reserve_late(jid,processing=True),self.current.replace(hour=18))
        self.assertEqual(planning.state()[0]['kind'],'sending')
        with core.db() as c:self.assertEqual(c.execute('SELECT stage FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()[0],'processing')

    def test_concurrent_reservations_have_unique_slots_and_daily_bounds(self):
        ids=[self.job(i)[1] for i in range(3)]
        with ThreadPoolExecutor(max_workers=3) as pool:slots=list(pool.map(planning.reserve_late,ids))
        self.assertEqual(len(set(slots)),3)
        self.assertEqual(sum(slot.date()==self.current.date() for slot in slots),2)

    def test_same_job_recovery_is_idempotent_and_persisted_across_restart(self):
        _,jid=self.job()
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(planning.reserve_late,[jid,jid]))
        core.init();autopilot.init();yt.init()
        self.assertEqual(planning.recover_overdue(),[])
        with core.db() as c:
            self.assertEqual(c.execute('SELECT changes FROM auto_schedule_changes WHERE job_id=?',(jid,)).fetchone()[0],1)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM operation_events WHERE kind='schedule'").fetchone()[0],1)

    def test_calendar_has_local_manual_remote_and_buffer_provenance(self):
        _,local=self.job();_,manual=self.job(1,automatic=False)
        _,remote=self.job(2);self.remote(remote,'scheduled')
        _,buffer=self.job(3)
        with core.db() as c:c.execute("UPDATE auto_jobs SET delivery='draft',buffer_id='draft-test' WHERE job_id=?",(buffer,))
        plans={p['id']:p for p in planning.state()}
        self.assertEqual(plans[local]['kind'],'local');self.assertEqual(plans[manual]['kind'],'manual')
        self.assertEqual(plans[remote]['kind'],'remote');self.assertEqual(plans[buffer]['destination'],'buffer')

    def test_reservation_preserves_script_file_attestation_and_editorial_decision(self):
        pid,jid=self.job();before=core.get_job(jid)
        with core.db() as c:
            c.execute('INSERT INTO editorial_reviews VALUES (?,?,?,?,?)',(jid,'approved','fingerprint','Nota do editor',core.stamp()))
            c.execute('INSERT INTO media_validations VALUES (?,?,?,?,?,?,?,?,?)',(jid,'fixture-sha',100,1,1280,720,20,'fixture-content',core.stamp()))
            c.execute('UPDATE auto_jobs SET render_failures=2 WHERE job_id=?',(jid,))
        planning.reserve_late(jid)
        self.assertEqual(core.get_job(jid)['scenes'],before['scenes'])
        self.assertEqual(core.get_job(jid)['caption'],before['caption'])
        with core.db() as c:
            self.assertEqual(c.execute('SELECT note FROM editorial_reviews WHERE job_id=?',(jid,)).fetchone()[0],'Nota do editor')
            self.assertEqual(c.execute('SELECT sha256 FROM media_validations WHERE job_id=?',(jid,)).fetchone()[0],'fixture-sha')
            self.assertEqual(c.execute('SELECT render_failures FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()[0],2)

    def test_full_backlog_still_recovers_missed_slots_before_selecting_new_work(self):
        ids=[self.job(i)[1] for i in range(3)]
        self.assertIsNone(autopilot.cycle())
        self.assertTrue(all(datetime.fromisoformat(core.get_job(jid)['due_at'])>self.current for jid in ids))

    def test_no_slot_within_horizon_keeps_original_reservation(self):
        autopilot.put_settings({'daily_limit':1,'hours':[18]})
        _,jid=self.job();before=core.get_job(jid)['due_at']
        for day in range(8):self.job(day+1,due=(self.current+timedelta(days=day)).replace(hour=18))
        self.assertIsNone(planning.reserve_late(jid))
        self.assertEqual(core.get_job(jid)['due_at'],before)
        with core.db() as c:self.assertIsNone(c.execute('SELECT 1 FROM auto_schedule_changes WHERE job_id=?',(jid,)).fetchone())

    def test_overdue_utc_timestamp_is_recovered_by_instant_not_string_order(self):
        _,jid=self.job(due=datetime(2026,10,22,18,tzinfo=timezone.utc))
        self.assertEqual(planning.recover_overdue(),[jid])
        self.assertEqual(datetime.fromisoformat(core.get_job(jid)['due_at']),self.current.replace(hour=18))


if __name__=='__main__':unittest.main()
