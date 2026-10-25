"""Deterministic data reduction, before calibration outcomes are computed."""
import csv
import gzip
import hashlib
import io
import math
from array import array
from .common import PRIVATE,now,read_json,write_json,digest

def run():
    directory=PRIVATE/'datasets/streamflow'
    raw=directory/'data-output-topographic_lstm-topographic_lstm_preds_member_0.csv'
    with raw.open() as f:columns=next(csv.reader(f))
    stations=sorted(columns[1:],key=lambda x:hashlib.sha256(('oqo-streamflow-v1:'+x).encode()).hexdigest())[:24]
    positions=[columns.index(x) for x in stations];means={};m2={};dates=[]
    for member in range(10):
        path=directory/f'data-output-topographic_lstm-topographic_lstm_preds_member_{member}.csv'
        observed=[]
        with path.open() as f:
            reader=csv.reader(f)
            if next(reader)!=columns:raise ValueError('Ensemble columns differ')
            for row in reader:
                date=row[0]
                if not '2006-01-01'<=date<='2022-12-31':continue
                observed.append(date);v=[float(row[p]) for p in positions]
                if not all(math.isfinite(x) for x in v):raise ValueError('Nonfinite selected prediction')
                if member==0:means[date]=array('d',v);m2[date]=array('d',[0.0]*24)
                else:
                    for i,x in enumerate(v):
                        delta=x-means[date][i];means[date][i]+=delta/(member+1);m2[date][i]+=delta*(x-means[date][i])
        if member==0:dates=observed
        elif observed!=dates:raise ValueError('Ensemble dates differ')
    if len(set(dates))!=len(dates):raise ValueError('Duplicate prediction dates')
    with (directory/'data-processed-static_attributes.csv').open() as f:
        attrs={r['station_id']:float(r['basin_area_km2']) for r in csv.DictReader(f)}
    if any(not attrs.get(s,0)>0 for s in stations):raise ValueError('Missing basin area')
    target=directory/'calibration-input.csv.gz';missing={s:0 for s in stations};valid={s:0 for s in stations}
    with (directory/'data-processed-combined_streamflow.csv').open() as f,target.open('wb') as disk:
        with gzip.GzipFile(filename='',fileobj=disk,mode='wb',mtime=0) as gz:
            with io.TextIOWrapper(gz,encoding='utf-8',newline='') as out:
                writer=csv.writer(out);writer.writerow(['date','station','calibration_group','mean_mm_day','spread_mm_day','observed_mm_day'])
                reader=csv.DictReader(f);seen=set()
                for row in reader:
                    date=row.get('Date') or row.get('date') or row[reader.fieldnames[0]]
                    if date not in means:continue
                    if date in seen:raise ValueError('Duplicate observation date')
                    seen.add(date)
                    for i,s in enumerate(stations):
                        text=row.get(s,'');obs=float(text) if text and text.lower()!='nan' else None
                        if obs is None or not math.isfinite(obs) or obs<0:missing[s]+=1;continue
                        obs*=86.4/attrs[s];valid[s]+=1
                        writer.writerow([date,s,'calibration' if i<12 else 'evaluation',format(means[date][i],'.12g'),format(math.sqrt(max(0,m2[date][i])/9),'.12g'),format(obs,'.12g')])
    record={'prepared_at':now(),'selection':'24 lowest SHA256(oqo-streamflow-v1:station_id); first 12 calibration, other 12 evaluation; no outcome-based substitution',
      'stations':stations,'calibration_stations':stations[:12],'evaluation_stations':stations[12:],
      'predictor_dates':[dates[0],dates[-1]],'predictor_date_count':len(dates),'valid_rows_by_station':valid,'missing_or_invalid_observations':missing,
      'prediction_aggregation':'Welford mean and sample standard deviation, 10 members, ddof=1',
      'observation_conversion':'m3/s * 86.4 / basin_area_km2 = mm/day',
      'posthoc_training_end':'2012-12-31','evaluation_start':'2013-01-01',
      'qualification_scope':'Schema, units, date alignment, finite values, missingness; calibration comparisons not computed',
      'spatial_holdout_scope':'Stations held out from this posthoc calibrator only; all were in original regional LSTM training',
      'file':str(target.relative_to(PRIVATE)),'sha256':digest(target.read_bytes()),'bytes':target.stat().st_size,
      'acquisition_manifest_sha256':digest((directory/'acquisition.json').read_bytes())}
    write_json(directory/'qualification.json',record);print({k:record[k] for k in ['stations','predictor_dates','predictor_date_count','bytes','sha256']})

if __name__=='__main__':run()
