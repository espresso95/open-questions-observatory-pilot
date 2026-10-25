import json
import tempfile
import unittest
import shutil
from pathlib import Path
from engine.common import write_json,read_json
from engine.supervisor import Supervisor

class SupervisorState(unittest.TestCase):
    def setup_state(self,d,budget=300):
        s=Supervisor(d)
        self.addCleanup(s.db.close)
        write_json(Path(d)/'config.json',{'lease_seconds':180,'daily_execution_seconds':budget,'max_attempts':3,'plans':{}})
        return s

    def test_claim_is_exclusive_and_expired_lease_preserves_attempts(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.setup_state(d);b=Supervisor(d);self.addCleanup(b.db.close);a.enqueue('integrity','snapshot',10,1000)
            first=a.claim(1000);self.assertEqual(first['attempt'],1);self.assertIsNone(b.claim(1001))
            b.recover(1181);second=a.claim(1181);self.assertEqual(second['attempt'],2)
            spent,reserved=a.db.execute('SELECT seconds,reserved FROM usage').fetchone()
            self.assertEqual((spent,reserved),(5,5))

    def test_budget_is_reserved_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            s=self.setup_state(d,budget=119);s.enqueue('reproduce','frozen',10,1000)
            self.assertIsNone(s.claim(1000));self.assertEqual(s.db.execute('SELECT attempts FROM jobs').fetchone()[0],0)

    def test_unknown_work_cannot_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            s=self.setup_state(d)
            with self.assertRaises(ValueError):s.perform({'kind':'execute_paper_instructions'})

    def test_completed_backup_is_verified_and_reused_on_retry(self):
        with tempfile.TemporaryDirectory() as d:
            s=self.setup_state(d);first=s.backup('2026-10-25');second=s.backup('2026-10-25')
            self.assertEqual(first['sha256'],second['sha256']);self.assertTrue(second['reused_verified_snapshot'])
            self.assertIn('2026-10-25.config.json',second['files'])

    def test_uncommitted_partial_backup_is_preserved_before_retry(self):
        with tempfile.TemporaryDirectory() as d:
            s=self.setup_state(d);directory=Path(d)/'backups';directory.mkdir()
            (directory/'2026-10-25.sqlite3').write_bytes(b'partial snapshot')
            (directory/'2026-10-25-contexts').mkdir()
            result=s.backup('2026-10-25');self.assertEqual(result['restored_integrity_check'],'ok')
            preserved=list(directory.glob('incomplete-*/2026-10-25.sqlite3'))
            self.assertEqual(len(preserved),1);self.assertEqual(preserved[0].read_bytes(),b'partial snapshot')

    def test_committed_backup_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            s=self.setup_state(d);s.backup('2026-10-25')
            (Path(d)/'backups/2026-10-25.config.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):s.backup('2026-10-25')

    def test_restored_inflight_backup_job_completes_without_duplicate_backup(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as restored_dir:
            s=self.setup_state(d);s.enqueue('backup','2026-10-25',99,1000);job=s.claim(1000)
            receipt=s.backup('2026-10-25');source=Path(d)/'backups'
            shutil.copytree(source,Path(restored_dir)/'backups')
            shutil.copy2(source/'2026-10-25.sqlite3',Path(restored_dir)/'state.sqlite3')
            shutil.copy2(source/'2026-10-25.config.json',Path(restored_dir)/'config.json')
            restored=Supervisor(restored_dir);self.addCleanup(restored.db.close)
            restored.recover(1200);replay=restored.claim(1200);self.assertEqual(replay['attempt'],2)
            result=restored.perform(replay);restored.finish(replay,result,None,.01)
            self.assertTrue(result['reused_verified_snapshot'])
            self.assertEqual(restored.db.execute('SELECT state FROM jobs').fetchone()[0],'completed')
            self.assertEqual(s.db.execute('SELECT state FROM jobs').fetchone()[0],'running')

if __name__=='__main__':unittest.main()
