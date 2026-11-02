import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import animation_demos
import core
import story_library


class AnimationDemoGalleryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        change=patch.object(core,'DATA',Path(temporary.name));change.start();self.addCleanup(change.stop)
        self.identifier='a'*32;self.folder=core.DATA/'stories'/self.identifier;self.folder.mkdir(parents=True)
        self.meta={'animation_type':'motion_demo_3d','action':'handoff','duration':6,'fps':18,'sha256':'b'*64,
                   'native_project':'private-local-project.blend'}
        for name in ('video.mp4','poster.png'):(self.folder/name).write_bytes(b'fixture, not render evidence')
        self.write_meta()
        self.catalog=core.DATA/'animation-demos'/'catalog.json';self.catalog.parent.mkdir()
        self.write_catalog([{'id':self.identifier,'action':'handoff'}])

    def write_meta(self):
        (self.folder/'roteiro.json').write_text(json.dumps(self.meta),encoding='utf-8')

    def write_catalog(self,rows):
        self.catalog.write_text(json.dumps({'clips':rows}),encoding='utf-8')

    def test_ready_demo_is_watchable_but_never_enters_episode_library(self):
        rows=animation_demos.state()
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['duration'],6)
        self.assertIn('/stories/'+self.identifier+'/video.mp4',rows[0]['video_url'])
        self.assertNotIn('private-local-project',json.dumps(rows))
        self.assertEqual(story_library.entries(),[])

    def test_missing_or_mislabeled_deliverables_are_not_advertised(self):
        for field,value in (('episode',2),('duration',True),('duration',float('nan')),('duration',31),
                            ('fps',True),('fps',0),('sha256','invalid'),('action','other'),('animation_type','still')):
            original=dict(self.meta);self.meta[field]=value;self.write_meta()
            with self.subTest(field=field,value=value):self.assertEqual(animation_demos.state(),[])
            self.meta=original
        self.write_meta();(self.folder/'poster.png').unlink()
        self.assertEqual(animation_demos.state(),[])

    def test_catalog_cannot_inject_paths_duplicates_or_arbitrary_titles(self):
        valid={'id':self.identifier,'action':'handoff','title':'<script>not trusted</script>'}
        self.write_catalog([None,{'id':'../../secret','action':'handoff'},{'id':self.identifier,'action':[]},valid,valid])
        rows=animation_demos.state();self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['title'],'A entrega da chave')
        for payload in ('[]','invalid',json.dumps({'clips':'bad'})):
            self.catalog.write_text(payload,encoding='utf-8');self.assertEqual(animation_demos.state(),[])


if __name__=='__main__':unittest.main()
