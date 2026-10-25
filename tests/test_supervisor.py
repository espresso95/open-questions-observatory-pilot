import json
import tempfile
import unittest
from pathlib import Path
from engine.common import write_json
from engine.supervisor import Supervisor

class SupervisorState(unittest.TestCase):
    def setup_state(self,d,budget=300):
        s=Supervisor(d)
        write_json(Path(d)/'config.json',{'lease_seconds':180,'daily_execution_seconds':budget,'max_attempts':3})
        return s

    def test_claim_is_exclusive_and_expired_lease_preserves_attempts(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.setup_state(d);b=Supervisor(d);a.enqueue('integrity','snapshot',10,1000)
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

if __name__=='__main__':unittest.main()
