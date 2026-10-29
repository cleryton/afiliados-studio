from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import core
import story_director as director
import story_motion
from story_week_catalog import STORIES,NEXT_NUMBERS,caption


class StoryDirectorTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,28,12,tzinfo=timezone.utc)

    def post(self,n,**changes):
        return {'url':f'https://www.tiktok.com/@fixture/video/{n}',
                'observed_at':self.now.isoformat(),'published_at':(self.now-timedelta(hours=25)).isoformat(),
                'views':100,'duration':60,'average_watch':12,**changes}

    def test_small_young_stale_or_unknown_samples_do_not_drive_automatic_changes(self):
        cases=[[],[self.post(1)],[self.post(1)]*4,
               [self.post(n,views=99) for n in range(3)],
               [self.post(n,average_watch=None) for n in range(3)],
               [self.post(n,published_at=(self.now-timedelta(hours=5)).isoformat()) for n in range(3)],
               [self.post(n,observed_at=(self.now-timedelta(days=20)).isoformat(),published_at=(self.now-timedelta(days=22)).isoformat()) for n in range(3)]]
        for posts in cases:
            with self.subTest(posts=posts):
                result=director.policy(posts,self.now)
                self.assertFalse(result['has_evidence']);self.assertEqual(result['mode'],'balanced')

    def test_mature_distinct_data_suggests_only_one_bounded_experiment(self):
        result=director.policy([self.post(n) for n in range(3)],self.now)
        self.assertTrue(result['has_evidence']);self.assertEqual(result['mode'],'compact')
        self.assertEqual(result['shot_seconds'],2.5);self.assertEqual(result['speech_rate'],0)
        original=deepcopy(STORIES[9]);story,report=director.plan(original,result)
        self.assertIn(story['scenes'][0]['text'],STORIES[9]['hooks'])
        self.assertEqual(story['scenes'][0]['text'],director.plan(original)[0]['scenes'][0]['text'])
        self.assertEqual(original,STORIES[9]);self.assertIsNone(report['performance_prediction'])

    def test_new_scripts_have_distinct_complete_stories_and_preserve_offer_disclosure(self):
        hooks=set();scripts=set()
        offer={'name':'Curso autorizado','facts':['Fato verificado.'],'url':'https://example.com/own-affiliate'}
        for n in NEXT_NUMBERS:
            story,report=director.plan(STORIES[n]);hooks.add(report['hook']);scripts.add(report['script_sha256'])
            self.assertEqual(story['scenes'][-1]['beat'],'payoff')
            text=caption(n,offer,story)
            self.assertIn(offer['url'],text);self.assertIn('PUBLICIDADE',text)
            self.assertIn('não são clientes nem depoimentos',text);self.assertLess(len(text),2200)
        self.assertEqual(len(hooks),7);self.assertEqual(len(scripts),7)
        bad=deepcopy(STORIES[9]);bad['scenes'][-1]['beat']='tease'
        with self.assertRaises(ValueError):director.plan(bad)

    def test_real_word_starts_replace_estimated_caption_boundaries_without_gaps(self):
        text='Uma chave estava na mesa. Lia abriu a porta e encontrou a irmã esperando.'
        import re
        rows=[{'position':m.start(),'seconds':i*.4,'length':len(m.group())} for i,m in enumerate(re.finditer(r'\S+',text))]
        cards,methods=director.timed_cards([text],[8],[rows])
        self.assertEqual(methods,['sapi_word_boundaries']);self.assertEqual(cards[0]['start'],0)
        self.assertEqual(cards[-1]['end'],8)
        self.assertTrue(all(a['end']==b['start'] for a,b in zip(cards,cards[1:])))
        if len(cards)>1:
            first=cards[1]['text'].split()[0];offset=text.index(first)
            wanted=next(r['seconds'] for r in rows if r['position']==offset)
            self.assertAlmostEqual(cards[1]['start'],round(wanted*24)/24)

    def test_incomplete_unsorted_or_corrupt_word_events_fall_back_explicitly(self):
        text='Uma chave estava na mesa. Lia abriu a porta e encontrou a irmã esperando.'
        for rows in ([],None,[{'position':0,'seconds':0,'length':3}],
                     [{'position':0,'seconds':float('nan')}],[{'position':0,'seconds':-1}]):
            with self.subTest(rows=rows):
                cards,methods=director.timed_cards([text],[8],[rows])
                self.assertEqual(methods,['estimated_by_text']);self.assertEqual(cards[-1]['end'],8)

    def test_reframe_cuts_cover_timeline_and_never_exceed_policy(self):
        episode={'director':{'policy':director.policy([self.post(n) for n in range(3)],self.now)}}
        for duration in (2.5,6.125,17):
            shots=story_motion.clip_shots({'visual':'drawing'},duration,episode)
            self.assertEqual(shots[0]['start_frame'],0);self.assertEqual(shots[-1]['end_frame'],round(duration*24))
            self.assertTrue(all(0<s['end_frame']-s['start_frame']<=60 for s in shots))
            self.assertTrue(all(1<=s['zoom']<=1.16 for s in shots))
            self.assertTrue(all(a['end_frame']==b['start_frame'] for a,b in zip(shots,shots[1:])))

    def test_no_voice_long_hook_and_unreadable_captions_stop_release(self):
        _,report=director.plan(STORIES[9])
        good=[{'start':i*5,'end':(i+1)*5,'text':'Texto legível.'} for i in range(6)]
        self.assertEqual(director.review(report,[5]*6,good,[True]*6)['status'],'render_checked')
        for durations,cards,voice in (([8]*6,good,[True]*6),([5]*6,good,[False]*6),
                                      ([5]*6,[{'start':0,'end':.1,'text':'Texto longo demais.'}],[True]*6)):
            with self.assertRaises(ValueError):director.review(report,durations,cards,voice)

    def test_actual_moving_clip_is_cut_decodable_and_keeps_expected_duration(self):
        import imageio_ffmpeg
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);exe=imageio_ffmpeg.get_ffmpeg_exe();clip=directory/'source.mp4'
            subprocess.run([exe,'-y','-v','error','-f','lavfi','-i','testsrc2=s=180x320:r=12:d=1',
                            '-c:v','libx264','-pix_fmt','yuv420p',str(clip)],check=True,capture_output=True,timeout=30,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            episode={'director':{'policy':director.policy()}}
            output=story_motion.render_background(exe,episode,0,{'visual':'drawing'},7,None,directory,{'path':clip})
            result=subprocess.run([exe,'-v','info','-i',str(output),'-f','null','-'],capture_output=True,timeout=40,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(result.returncode,0);self.assertIn(b'720x1280',result.stderr)
            self.assertIn(b'Duration: 00:00:07.00',result.stderr)
