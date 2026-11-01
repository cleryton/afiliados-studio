import json
from pathlib import Path
import tempfile
import unittest
from scripts import configure_browser_access as access


class BrowserAccessTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.project=self.root/'project';self.project.mkdir()
        self.config=self.root/'.mcp.json'
        self.original={'mcpServers':{'chrome-devtools':{'command':'npx','args':['-y','chrome-devtools-mcp@1.10.1']},
                                    'other':{'command':'example','env':{'EXAMPLE_VALUE':'fixture-private-value'}}}}
        self.config.write_text(json.dumps(self.original),encoding='utf-8')

    def test_preview_has_no_side_effect_on_integration_and_preserves_other_servers(self):
        before=self.config.read_bytes();result=access.plan(self.config,self.project)
        self.assertTrue(result['changed']);self.assertEqual(self.config.read_bytes(),before)
        self.assertEqual(result['value']['mcpServers']['other'],self.original['mcpServers']['other'])

    def test_apply_adds_only_the_project_story_folder_and_is_idempotent(self):
        original=self.config.read_bytes();access.apply(self.config,self.project)
        after=self.config.read_bytes();result=access.apply(self.config,self.project)
        self.assertFalse(result['changed']);self.assertEqual(self.config.read_bytes(),after)
        args=json.loads(after)['mcpServers']['chrome-devtools']['args']
        self.assertEqual(args, ['-y','chrome-devtools-mcp@1.10.1','--workspace='+str((self.project/'data'/'stories').resolve())])
        backup=self.config.with_name('.mcp.json.before-story-access')
        self.assertEqual(backup.read_bytes(),original)
        self.assertNotIn('--allow-unrestricted-paths',args)

    def test_existing_workspace_alias_is_recognized_without_another_grant(self):
        folder=access.video_root(self.project)
        value=self.original;value['mcpServers']['chrome-devtools']['args']+=['--filesystem-root',str(folder)]
        self.config.write_text(json.dumps(value),encoding='utf-8')
        self.assertFalse(access.plan(self.config,self.project)['changed'])

    def test_unrestricted_mode_or_unpinned_package_is_not_silently_changed(self):
        for option in ('--allow-unrestricted-paths','--allowUnrestrictedPaths=true','chrome-devtools-mcp@latest'):
            value=json.loads(json.dumps(self.original))
            if option.endswith('@latest'):value['mcpServers']['chrome-devtools']['args']=['-y',option]
            else:value['mcpServers']['chrome-devtools']['args'].append(option)
            self.config.write_text(json.dumps(value),encoding='utf-8');before=self.config.read_bytes()
            with self.assertRaises(ValueError):access.apply(self.config,self.project)
            self.assertEqual(self.config.read_bytes(),before)

    def test_invalid_or_unrelated_configuration_is_unchanged(self):
        for text in ('not json','{}','[]','{"mcpServers":[]}','{"mcpServers":{"chrome-devtools":{"args":"not a list"}}}'):
            self.config.write_text(text,encoding='utf-8')
            with self.assertRaises(ValueError):access.apply(self.config,self.project)
            self.assertEqual(self.config.read_text(encoding='utf-8'),text)

    def test_linked_data_folder_cannot_create_files_outside_project(self):
        outside=self.root/'outside';outside.mkdir()
        try:(self.project/'data').symlink_to(outside,target_is_directory=True)
        except OSError:self.skipTest('Este Windows não permite criar links no teste.')
        with self.assertRaises(ValueError):access.apply(self.config,self.project)
        self.assertFalse((outside/'stories').exists())


if __name__=='__main__':unittest.main()
