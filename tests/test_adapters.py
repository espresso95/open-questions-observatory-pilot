import copy
import io
import math
import tempfile
import unittest
import zipfile
import gzip
from collections import deque
from pathlib import Path
from engine.adapters.prefix import certify,generators,compose
from engine.adapters.streamflow import fit
from engine.archive import RemoteZip
from engine.input_support import streamflow as input_support

def brute_order(gens):
    identity=tuple(range(len(gens[0])));seen={identity};todo=deque([identity])
    while todo:
        p=todo.popleft()
        for g in gens:
            q=compose(g,p)
            if q not in seen:seen.add(q);todo.append(q)
    return len(seen)

class Adapters(unittest.TestCase):
    def test_input_support_does_not_require_evaluation_outcomes(self):
        p={'calibration_end':'2012-12-31','evaluation_start':'2013-01-01','evaluation_end':'2022-12-31',
          'flow_bin_edges':[.8,.9],'minimum_high_rows_per_station':2,'minimum_evaluation_stations':8}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'input.csv.gz'
            with gzip.open(path,'wt') as f:
                f.write('date,station,calibration_group,mean_mm_day\n2010-01-01,A,calibration,1\n2010-01-02,A,calibration,2\n2015-01-01,B,evaluation,3\n2015-01-02,B,evaluation,4\n')
            support=input_support(path,p)
            self.assertFalse(support['qualified']);self.assertEqual(support['eligible_stations'],1)
            self.assertFalse(support['uses_evaluation_errors'])
    def test_exact_certificates_agree_with_exhaustive_small_groups(self):
        for n in (6,7):
            for k in range(2,n-1):
                for m in range(k+1,n):
                    expected=brute_order(generators(n,m,k))==math.factorial(n)
                    result=certify(n,m,k,30)['classification']
                    if result!='unknown':self.assertEqual(result=='symmetric',expected,(n,m,k))
        self.assertEqual(certify(6,3,2)['reason'],'imprimitive')
        self.assertEqual(certify(131,130,129,20)['classification'],'symmetric')

    def test_evaluation_targets_cannot_change_fitted_calibration(self):
        p={'calibration_end':'2012-12-31','minimum_calibration_rows':10,'flow_bin_edges':[.8,.9],
          'minimum_bin_rows':1,'target_coverage':.9,'spread_floor':.001}
        rows=[{'group':'calibration','date':'2010-01-01','mean':i,'spread':1,'observed':i+1} for i in range(100)]
        rows.append({'group':'evaluation','date':'2020-01-01','mean':10000,'spread':1,'observed':-999999})
        baseline=fit(rows,p);rows[-1]['observed']=999999999
        self.assertEqual(fit(rows,p),baseline)
        rows.append({'group':'calibration','date':'2020-01-01','mean':99999,'spread':1,'observed':9999999})
        self.assertEqual(fit(rows,p),baseline)

    def test_remote_zip_member_integrity_and_decompression_budget(self):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('data.csv',b'a,b\n1,2\n'*1000)
        data=buffer.getvalue()
        class FakeBroker:
            policy={'budgets':{'max_response_bytes':100}}
            def fetch(self,url,**kwargs):
                start,end=kwargs['byte_range']
                return data[start:end+1],{'content_range':f'bytes {start}-{end}/{len(data)}'}
        archive=RemoteZip(FakeBroker(),'https://example.org/archive.zip',len(data),{'analyze':True})
        with self.assertRaises(ValueError):archive.read('data.csv',max_bytes=100)
        raw,record=archive.read('data.csv');self.assertEqual(raw,b'a,b\n1,2\n'*1000)

if __name__=='__main__':unittest.main()
