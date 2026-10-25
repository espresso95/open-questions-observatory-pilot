import copy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from engine.common import ROOT,read_json,write_json
from engine import public_validate

class Registry(unittest.TestCase):
    def fixture(self,directory):
        target=Path(directory)
        releases=read_json(ROOT/'publication/releases.json')['releases']
        paths={'publication/releases.json'}
        for release in releases:paths.update([*release['immutable_paths'],release['approved_manifest']])
        for rel in sorted(paths):
            p=target/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
        return target

    def test_frozen_science_survives_implementation_maintenance(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);(root/'README.md').write_text('Maintained implementation documentation')
            with patch.object(public_validate,'ROOT',root):public_validate.main()

    def test_changed_research_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d)
            next((root/'research').glob('*/results.json')).write_text('{}')
            with patch.object(public_validate,'ROOT',root),self.assertRaises(SystemExit):public_validate.main()

    def test_unapproved_scientific_addition_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/'research/unapproved/report.md';p.parent.mkdir();p.write_text('New claim')
            with patch.object(public_validate,'ROOT',root),self.assertRaises(SystemExit):public_validate.main()

    def test_registered_attempt_must_resolve_to_its_exact_plan(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);path=root/'publication/releases.json';registry=read_json(path)
            release=registry['releases'][0]
            release['run_locations']={release['run_ids'][0]:'research/missing-attempt'}
            write_json(path,registry)
            with patch.object(public_validate,'ROOT',root),self.assertRaises(SystemExit):public_validate.main()

if __name__=='__main__':unittest.main()
