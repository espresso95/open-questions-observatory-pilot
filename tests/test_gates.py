import copy
import tempfile
import unittest
from pathlib import Path
from engine.common import ROOT,PRIVATE,read_json
from engine.broker import allowed_url,validate_evidence
from engine.policy import validate_question,validate_sources,bundle_manifest,require_disclosure_approval
from engine.analysis import load,solve

class Gates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q=read_json(ROOT/'review-bundle/catalog/questions/Q-ENSO-001/question.json')
        cls.sources={s['id']:s for s in read_json(PRIVATE/'acquisition.json')}

    def test_fabricated_quote_rejected(self):
        item=copy.deepcopy(self.q['source_evidence'][0]);item['quote']='Fabricated scientific finding'
        with self.assertRaises(ValueError):validate_evidence(item,self.sources)

    def test_unknown_rights_rejected(self):
        sources=copy.deepcopy(list(self.sources.values()));sources[0]['rights']['export']=None
        with self.assertRaises(ValueError):validate_sources(sources)

    def test_unknown_rating_or_blocker_prevents_dispatch(self):
        for mutate in ['unknown','blocker']:
            q=copy.deepcopy(self.q)
            if mutate=='unknown':q['assessment']['ratings']['input_readiness']=None
            else:q['assessment']['blockers']=['lab required']
            with self.assertRaises(ValueError):validate_question(q)

    def test_computation_cannot_claim_scientific_resolution(self):
        q=copy.deepcopy(self.q);q['resolved']=True
        with self.assertRaises(ValueError):validate_question(q)

    def test_unconfigured_local_or_credential_url_denied(self):
        allowed={s['url'] for s in self.sources.values()}
        for url in ['http://127.0.0.1','https://localhost/','https://user:pass@psl.noaa.gov/','https://psl.noaa.gov/unapproved']:
            self.assertFalse(allowed_url(url,allowed))

    def test_approval_binds_current_content(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'report.md').write_text('Initial result')
            with self.assertRaises(ValueError):require_disclosure_approval(p,None)
            a={'approved_sha256':bundle_manifest(p)['sha256'],'human_approver':'test fixture only'}
            require_disclosure_approval(p,a)
            (p/'report.md').write_text('Changed result')
            with self.assertRaises(ValueError):require_disclosure_approval(p,a)

    def test_secret_and_symlink_export_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);f=p/'report.md';f.write_text('ghp_'+'x'*30)
            with self.assertRaises(ValueError):bundle_manifest(p)
            f.unlink();f.symlink_to(ROOT/'README.md')
            with self.assertRaises(ValueError):bundle_manifest(p)

    def test_internal_missing_and_duplicate_month_rejected(self):
        source=PRIVATE/self.sources['D-NINO34']['raw_path']
        text=source.read_text()
        lines=text.splitlines()
        index=next(i for i,line in enumerate(lines) if line.split() and line.split()[0]=='2005')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.data'
            fields=lines[index].split();fields[3]='-99.99'
            altered=lines[:];altered[index]=' '.join(fields);p.write_text('\n'.join(altered))
            with self.assertRaises(ValueError):load(p)
            altered=lines[:];altered.insert(index,lines[index]);p.write_text('\n'.join(altered))
            with self.assertRaises(ValueError):load(p)

    def test_solver_uses_pivoting(self):
        self.assertEqual(solve([[0.,1.],[1.,1.]],[2.,5.]),[3.,2.])

if __name__=='__main__':unittest.main()
