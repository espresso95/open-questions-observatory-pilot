import csv,gzip,math
from pathlib import Path
import numpy as np
import json
from datetime import datetime,timezone
def read_json(p):return json.loads(Path(p).read_text())
def now():return datetime.now(timezone.utc).isoformat()
p=Path(__file__).resolve().parent
plan=read_json(p/'plan.json');result=read_json(p/'run-primary.json')['results'];params=plan['parameters']
with gzip.open(p/'input.csv.gz','rt') as f:rows=list(csv.DictReader(f))
means=np.array([float(r['mean_mm_day']) for r in rows]);spread=np.array([float(r['spread_mm_day']) for r in rows]);obs=np.array([float(r['observed_mm_day']) for r in rows]);dates=np.array([r['date'] for r in rows]);groups=np.array([r['calibration_group'] for r in rows]);stations=np.array([r['station'] for r in rows])
cal=(groups=='calibration')&(dates<=params['calibration_end']);evaluation=(groups=='evaluation')&(dates>=params['evaluation_start'])&(dates<=params['evaluation_end'])
def q(x,prob):return float(np.sort(x)[min(len(x),math.ceil((len(x)+1)*prob))-1])
edges=[q(means[cal],prob) for prob in params['flow_bin_edges']]
z=np.abs(obs[cal]-means[cal])/np.maximum(spread[cal],params['spread_floor']);bins=np.searchsorted(edges,means[cal],side='right')
model={'edges':edges,'global':q(z,.9),'conditional':[q(z[bins==i],.9) for i in range(3)]}
errors=[abs(model['global']-result['model']['global'])]+[abs(a-b) for a,b in zip(model['conditional'],result['model']['conditional'])]
assert max(errors)<1e-12 and edges==result['model']['edges']
high=evaluation&(means>=edges[-1]);counts={s:int(np.sum(high&(stations==s))) for s in sorted(set(stations[evaluation]))}
assert counts=={r['station']:r['high_rows'] for r in result['station_eligibility']}
assert sum(n>=params['minimum_high_rows_per_station'] for n in counts.values())==result['eligible_station_count']==3
assert result['primary_endpoint_evaluated'] is False and result['status']=='inconclusive'
receipt={'verified_at':now(),'independent_library':'NumPy '+np.__version__,'max_calibration_multiplier_difference':max(errors),'bin_edges_identical':True,'station_high_flow_counts_identical':True,'eligible_stations':3,'required_stations':8,'primary_endpoint_not_evaluated':True,'interpretation':'Insufficient independent station support for the frozen primary endpoint; no thresholds lowered','scientific_review':False}
print(json.dumps(receipt,sort_keys=True))
