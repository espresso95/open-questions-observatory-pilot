import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from engine.common import ROOT,read_json,now
from engine.retrieval import Broker,RetrievalDenied,QuotaExhausted,ProviderUnavailable
from types import SimpleNamespace

class Retrieval(unittest.TestCase):
    def test_missing_rights_blocks_without_request(self):
        with tempfile.TemporaryDirectory() as d:
            b=Broker(d)
            with self.assertRaises(RetrievalDenied):b.fetch('https://arxiv.org/abs/1')
            self.assertEqual(b.db.execute('SELECT COUNT(*) FROM usage').fetchone()[0],0)

    def test_private_resolution_and_credential_urls_denied(self):
        with tempfile.TemporaryDirectory() as d:
            b=Broker(d)
            with self.assertRaises(RetrievalDenied):b.validate('https://secret@arxiv.org/abs/1')
            with patch('socket.getaddrinfo',return_value=[(0,0,0,'',('127.0.0.1',443))]),self.assertRaises(RetrievalDenied):
                b.validate('https://arxiv.org/abs/1')

    def test_concurrent_worst_case_reservation_never_overspends(self):
        with tempfile.TemporaryDirectory() as d:
            p=copy.deepcopy(read_json(ROOT/'config/providers.json'));p['budgets']['bytes_per_day']=100;p['budgets']['max_response_bytes']=70
            a=Broker(d,p);b=Broker(d,p)
            self.assertEqual(a.reserve('data',0)[1],70)
            self.assertEqual(b.reserve('data',0)[1],30)
            with self.assertRaises(QuotaExhausted):a.reserve('data',0)

    def test_fulltext_quota_is_a_hard_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=copy.deepcopy(read_json(ROOT/'config/providers.json'));p['budgets']['fulltexts_per_day']=1
            b=Broker(d,p);b.reserve('fulltext',0)
            with self.assertRaises(QuotaExhausted):b.reserve('fulltext',0)

    def test_ranges_are_separate_cached_objects_and_must_match_response(self):
        with tempfile.TemporaryDirectory() as d:
            b=Broker(d)
            def response(args,**kwargs):
                path=Path(args[args.index('--dump-header')+1])
                path.write_text('HTTP/1.1 206 Partial Content\nContent-Range: bytes 0-2/10\n')
                return SimpleNamespace(returncode=0,stdout=b'abc')
            rights={'analyze':True}
            with patch.object(b,'validate',return_value=('arxiv.org','1.1.1.1')),patch('subprocess.run',side_effect=response):
                data,s=b.fetch('https://arxiv.org/file',rights=rights,byte_range=(0,2))
                self.assertEqual(data,b'abc')
                with self.assertRaises(ProviderUnavailable):b.fetch('https://arxiv.org/file',rights=rights,byte_range=(3,5))
                self.assertEqual(b.db.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0],1)
                self.assertEqual(b.db.execute('SELECT reserved_bytes FROM usage').fetchone()[0],0)

if __name__=='__main__':unittest.main()
