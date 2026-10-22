from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import autopilot
import core
import insights
import youtube_client as yt


class InsightsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=patch.object(core,'DATA',Path(self.temp.name));override.start();self.addCleanup(override.stop)
        core.init();autopilot.init();yt.init()
        yt.put({'enabled':True,'channel_id':'UC-test'})
        yt.secret_path('tokens').write_bytes(b'fixture-token-file-never-read-by-mocked-api')
        autopilot.put_settings({'enabled':True})
        self.pid=core.save_product({'name':'Produto de teste','kind':'physical','category':'Casa','description':'Características verificadas para o teste.','url':'https://example.com/p?af=original'})

    def published(self,index=0):
        from uuid import uuid4
        jid=uuid4().hex;video=f'video{index:06d}'
        with core.db() as c:
            c.execute("INSERT INTO jobs(id,product_id,status,scenes,caption,due_at,created_at,updated_at,published_at,clicks,revenue,views) VALUES (?,?,'published','[]','fixture',?,?,?,?,7,12.5,42)",(jid,self.pid,core.stamp(),core.stamp(),core.stamp(),core.stamp()))
            c.execute('INSERT INTO youtube_jobs(job_id,stage,video_id,updated_at) VALUES (?,?,?,?)',(jid,'published',video,core.stamp()))
        return jid,video

    def video(self,video,**kwargs):
        return {'id':video,'snippet':{'channelId':kwargs.get('channel','UC-test')},'status':{'privacyStatus':kwargs.get('privacy','public')},'statistics':kwargs.get('stats',{'viewCount':'120','likeCount':'5'})}

    def test_sync_records_public_counters_without_marking_affiliate_results(self):
        jid,video=self.published()
        with patch.object(yt,'api',return_value={'items':[self.video(video)]}) as api:self.assertEqual(insights.sync(),1)
        self.assertEqual(api.call_args.args[0].split('?')[0],'videos')
        item=insights.state()[0]
        self.assertEqual(item['views'],120);self.assertEqual(item['likes'],5);self.assertIsNone(item['comments'])
        job=core.get_job(jid)
        self.assertEqual(job['views'],42);self.assertEqual(job['clicks'],7);self.assertEqual(job['revenue'],12.5)
        self.assertIsNone(job['results_recorded_at'])

    def test_paused_or_tester_operation_never_queries(self):
        self.published()
        with patch.object(yt,'api') as api:
            with patch.object(core,'TESTER',True):self.assertEqual(insights.sync(),0)
            autopilot.put_settings({'enabled':False});self.assertEqual(insights.sync(),0)
        api.assert_not_called()

    def test_refresh_is_persistent_and_at_most_twenty_per_request(self):
        for i in range(21):self.published(i)
        def response(path):
            from urllib.parse import parse_qs,urlparse
            ids=parse_qs(urlparse(path).query)['id'][0].split(',')
            self.assertLessEqual(len(ids),20)
            return {'items':[self.video(v) for v in ids]}
        with patch.object(yt,'api',side_effect=response) as api:
            self.assertEqual(insights.sync(),20);self.assertEqual(insights.sync(),1);self.assertEqual(insights.sync(),0)
        self.assertEqual(api.call_count,2)

    def test_wrong_channel_private_or_missing_video_do_not_become_zero(self):
        for index in range(3):self.published(index)
        response={'items':[self.video('video000000',channel='other'),self.video('video000001',privacy='private')]}
        with patch.object(yt,'api',return_value=response):self.assertEqual(insights.sync(),0)
        self.assertTrue(all(item['views'] is None and item['status']=='unavailable' for item in insights.state()))

    def test_invalid_counters_are_rejected_and_zero_is_valid(self):
        for value in [-1,True,1.5,'NaN','1.5','-1',10**19,None]:self.assertIsNone(insights.counter(value))
        self.assertEqual(insights.counter('0'),0)
        _,video=self.published()
        with patch.object(yt,'api',return_value={'items':[self.video(video,stats={'viewCount':'0'})]}):self.assertEqual(insights.sync(),1)
        self.assertEqual(insights.state()[0]['views'],0)

    def test_failure_preserves_snapshot_and_uses_backoff_without_raw_error(self):
        _,video=self.published()
        with patch.object(yt,'api',return_value={'items':[self.video(video)]}):insights.sync()
        future=core.now()+timedelta(hours=7)
        with patch('core.now',return_value=future),patch.object(yt,'api',side_effect=ValueError('private-fixture-do-not-expose')) as api:
            self.assertEqual(insights.sync(),0);self.assertEqual(insights.sync(),0)
        self.assertEqual(api.call_count,1)
        row=insights.state()[0]
        self.assertEqual(row['views'],120);self.assertEqual(row['status'],'error')
        self.assertNotIn('private-fixture',json.dumps(row))

    def test_disconnect_during_read_prevents_old_account_snapshot(self):
        self.published()
        def response(_):yt.disconnect();return {'items':[self.video('video000000')]}
        with patch.object(yt,'api',side_effect=response):self.assertEqual(insights.sync(),0)
        self.assertEqual(insights.state(),[])

    def test_old_cached_counters_are_removed_after_thirty_days(self):
        _,video=self.published()
        with patch.object(yt,'api',return_value={'items':[self.video(video)]}):insights.sync()
        with patch('core.now',return_value=core.now()+timedelta(days=31)):self.assertEqual(insights.state(),[])

    def test_unconfirmed_uploads_are_not_queried_or_published_by_metrics(self):
        jid,_=self.published()
        with core.db() as c:c.execute("UPDATE youtube_jobs SET stage='uncertain' WHERE job_id=?",(jid,))
        with patch.object(yt,'api') as api:self.assertEqual(insights.sync(),0)
        api.assert_not_called();self.assertEqual(insights.state(),[])
