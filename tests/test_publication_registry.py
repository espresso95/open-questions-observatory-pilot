import copy
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from engine.common import ROOT,read_json
from engine import public_validate

class Registry(unittest.TestCase):
    def fixture(self,directory):
        target=Path(directory)
        release=read_json(ROOT/'publication/releases.json')['releases'][0]
        for rel in [*release['immutable_paths'],'manifest.json','publication/releases.json']:
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

if __name__=='__main__':unittest.main()
