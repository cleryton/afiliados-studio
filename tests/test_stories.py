import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import core
import stories
import story_renderer
import story_offers
import autopilot


class StoriesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=patch.object(core,'DATA',Path(self.temp.name));override.start();self.addCleanup(override.stop)
        core.init()

    def test_pilot_is_idempotent_and_separate_from_affiliate_jobs(self):
        first=stories.create_pilot();again=stories.create_pilot();s=stories.state()
        self.assertEqual(first['id'],again['id']);self.assertTrue(again['existing'])
        self.assertEqual(len(s['episodes']),3);self.assertEqual([e['number'] for e in s['episodes']],[1,2,3])
        self.assertEqual(core.state()['jobs'],[]);self.assertEqual(core.state()['products'],[])
        self.assertFalse(s['publishing_connected']);self.assertTrue(all(e['video_url'] is None for e in s['episodes']))
        self.assertTrue(s['episodes'][-1]['scenes'][-1]['text'].endswith('Fim.'))

    def test_queue_claims_once_and_preserves_episode_order(self):
        stories.create_pilot();first=stories.claim_next()
        self.assertEqual(first['number'],1);self.assertIsNone(stories.claim_next())
        with core.db() as c:c.execute("UPDATE story_episodes SET status='ready' WHERE id=?",(first['id'],))
        self.assertEqual(stories.claim_next()['number'],2)

    def test_worker_error_requires_retry_and_does_not_claim_publication(self):
        stories.create_pilot()
        with patch.object(story_renderer,'render',side_effect=OSError('private path must not appear')):stories.tick()
        episode=stories.state()['episodes'][0]
        self.assertEqual(episode['status'],'error');self.assertNotIn('private path',episode['error'])
        self.assertIsNone(episode['video_url']);stories.retry(episode['id'])
        self.assertEqual(stories.state()['episodes'][0]['status'],'queued')
        with self.assertRaises(ValueError):stories.retry(episode['id'])

    def test_restart_recovers_only_interrupted_local_episode(self):
        stories.create_pilot();first=stories.claim_next()
        with core.db() as c:c.execute("UPDATE story_episodes SET status='ready' WHERE number=2")
        stories.init();episodes=stories.state()['episodes']
        self.assertEqual(episodes[0]['id'],first['id']);self.assertEqual(episodes[0]['status'],'queued')
        self.assertEqual(episodes[1]['status'],'ready')

    def test_rebuild_is_local_idempotent_in_queue_and_preserves_other_episodes(self):
        stories.create_pilot();first=stories.claim_next()
        with core.db() as c:c.execute("UPDATE story_episodes SET status='ready'")
        stories.rebuild(first['id'])
        self.assertEqual([e['status'] for e in stories.state()['episodes']],['queued','ready','ready'])
        self.assertFalse(stories.state()['publishing_connected'])
        with self.assertRaises(ValueError):stories.rebuild(first['id'])
        self.assertEqual(stories.claim_next()['id'],first['id'])

    def test_unknown_media_and_traversal_are_rejected(self):
        for eid,name in [('../secret','video.mp4'),('a'*32,'../tokens.json'),('a'*32,'speech-0.wav')]:
            with self.subTest(eid=eid,name=name),self.assertRaises(ValueError):stories.media_file(eid,name)
        self.assertEqual(stories.media_file('a'*32,'video.mp4').parent.parent,core.DATA/'stories')

    def test_real_vertical_video_decodes_and_export_discloses_fiction_and_ai(self):
        episode={'id':'f'*32,'number':1,'title':'Teste local','series_title':'A chave do 12',
                 'scenes':json.dumps([{'text':'Uma chave estava na mesa.','visual':'key'},{'text':'Lia abriu a carta.','visual':'letter'}])}
        real_run=subprocess.run
        def run(command,*args,**kwargs):
            if command[0]=='powershell.exe':raise FileNotFoundError('Sem voz no teste')
            return real_run(command,*args,**kwargs)
        with patch('story_renderer.subprocess.run',side_effect=run):result=story_renderer.render(episode)
        folder=core.DATA/'stories'/episode['id']
        self.assertFalse(result['voice']);self.assertGreater(result['duration'],8)
        self.assertIn('Ficção original',(folder/'legenda.txt').read_text(encoding='utf-8'))
        self.assertIn('gerados por IA',(folder/'legenda.txt').read_text(encoding='utf-8'))
        self.assertTrue((folder/'poster.png').is_file());self.assertTrue((folder/'legendas.srt').is_file())
        meta=json.loads((folder/'roteiro.json').read_text(encoding='utf-8'))
        self.assertEqual(len(meta['sha256']),64);self.assertFalse(list(folder.glob('speech-*')))
        self.assertEqual(meta['editing_style'],'cinematic-local-v1')
        self.assertFalse(meta['character_animation'])
        self.assertEqual(len(meta['shot_timeline']),2)
        self.assertFalse(list(folder.glob('motion-*')))
        self.assertFalse(list(folder.glob('clip-*')));self.assertFalse(list(folder.glob('overlay-*')))

    def test_missing_assets_preserve_existing_video_and_clear_intermediates(self):
        episode={'id':'e'*32,'number':1,'scenes':json.dumps([{'text':'Uma carta.','visual':'key'}])}
        folder=core.DATA/'stories'/episode['id'];folder.mkdir(parents=True)
        (folder/'video.mp4').write_bytes(b'prior artifact')
        with patch.object(story_renderer,'asset_path',return_value=core.DATA/'missing.png'):
            with self.assertRaises(ValueError):story_renderer.render(episode)
        self.assertEqual((folder/'video.mp4').read_bytes(),b'prior artifact')

    def product(self):
        autopilot.init()
        pid=core.save_product({'name':'Curso de desenho','url':'https://example.com/curso?afid=fixture',
                              'kind':'digital','category':'Desenho','description':'Curso online de desenho para iniciantes. Possui aulas gravadas.'})
        autopilot.approve_product(pid,{'active':True,'approved':True})
        return pid

    def test_offer_requires_authorized_product_and_preserves_fiction_and_link(self):
        sid=stories.create_pilot()['id'];pid=self.product()
        payload={'series_id':sid,'product_id':pid,'approved':True}
        with self.assertRaises(ValueError):story_offers.attach({**payload,'approved':False})
        with core.db() as c:original=c.execute('SELECT scenes FROM story_episodes WHERE number=1').fetchone()[0]
        self.assertFalse(story_offers.attach(payload)['existing']);self.assertTrue(story_offers.attach(payload)['existing'])
        with core.db() as c:self.assertEqual(c.execute('SELECT scenes FROM story_episodes WHERE number=1').fetchone()[0],original)
        offer=story_offers.for_series(sid)
        self.assertIn('https://example.com/curso?afid=fixture',story_offers.caption(offer))
        self.assertIn('não são clientes nem depoimentos',story_offers.caption(offer))
        self.assertTrue(all(s['visual']=='offer' for s in story_offers.scenes(offer)))
        self.assertTrue(stories.state()['episodes'][0]['offer_current'])
        autopilot.approve_product(pid,{'active':False,'approved':True})
        with self.assertRaises(ValueError):story_offers.attach(payload)

    def test_revoked_or_changed_offer_hides_ready_export_until_rebuilt(self):
        sid=stories.create_pilot()['id'];pid=self.product()
        story_offers.attach({'series_id':sid,'product_id':pid,'approved':True})
        with core.db() as c:c.execute("UPDATE story_episodes SET status='ready' WHERE series_id=?",(sid,))
        self.assertIsNotNone(stories.state()['episodes'][0]['video_url'])
        with core.db() as c:c.execute('UPDATE products SET description=? WHERE id=?',('Características alteradas no cadastro original.',pid))
        episode=stories.state()['episodes'][0]
        self.assertFalse(episode['offer_current']);self.assertIsNone(episode['video_url'])
        self.assertFalse(story_offers.attach({'series_id':sid,'product_id':pid,'approved':True})['existing'])
        self.assertEqual(stories.state()['episodes'][0]['status'],'queued')

    def test_profile_hint_never_claims_publishing_connection(self):
        self.assertEqual(stories.set_profile({'handle':'@projeto_teste'})['handle'],'projeto_teste')
        s=stories.state();self.assertEqual(s['target_handle'],'projeto_teste');self.assertFalse(s['publishing_connected'])
        for handle in ('https://tiktok.com/@other','<script>','ab','bad/name'):
            with self.subTest(handle=handle),self.assertRaises(ValueError):stories.set_profile({'handle':handle})

    def test_real_offer_video_uses_neutral_card_and_preserves_affiliate_disclosure(self):
        episode={'id':'d'*32,'number':1,'title':'Teste comercial','series_title':'A chave do 12',
                 'scenes':json.dumps([{'text':'Lia encontrou uma carta.','visual':'key'}]),
                 'offer':{'name':'Curso de desenho','url':'https://example.com/curso?afid=fixture','facts':['Possui aulas gravadas.']}}
        real_run=subprocess.run
        def run(command,*args,**kwargs):
            if command[0]=='powershell.exe':raise FileNotFoundError('Sem voz no teste')
            return real_run(command,*args,**kwargs)
        with patch('story_renderer.subprocess.run',side_effect=run):result=story_renderer.render(episode)
        folder=core.DATA/'stories'/episode['id'];caption=(folder/'legenda.txt').read_text(encoding='utf-8')
        self.assertIn(episode['offer']['url'],caption);self.assertIn('PUBLICIDADE',caption)
        self.assertGreater(result['duration'],10)
        self.assertEqual(json.loads((folder/'roteiro.json').read_text(encoding='utf-8'))['offer'],episode['offer'])
