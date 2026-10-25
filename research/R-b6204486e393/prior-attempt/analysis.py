"""Fixed posthoc calibration transfer experiment. Standard library, offline."""
import bisect
import csv
import gzip
import json
import math
import random
import statistics
import sys

def quantile(values,prob):
    values=sorted(values)
    if not values:raise ValueError('Empty calibration stratum')
    # Finite sample upper order statistic; dependence precludes a coverage guarantee.
    return values[min(len(values),math.ceil((len(values)+1)*prob))-1]

def fit(rows,parameters):
    calibration=[r for r in rows if r['group']=='calibration' and r['date']<=parameters['calibration_end']]
    if len(calibration)<parameters['minimum_calibration_rows']:raise ValueError('Insufficient calibration inputs')
    edges=[quantile([r['mean'] for r in calibration],p) for p in parameters['flow_bin_edges']]
    if len(set(edges))!=len(edges):raise ValueError('Degenerate flow bins')
    scores=[abs(r['observed']-r['mean'])/max(r['spread'],parameters['spread_floor']) for r in calibration]
    by_bin=[[] for _ in range(len(edges)+1)]
    for r,z in zip(calibration,scores):by_bin[bisect.bisect_right(edges,r['mean'])].append(z)
    if min(map(len,by_bin))<parameters['minimum_bin_rows']:raise ValueError('Insufficient conditional calibration rows')
    return {'edges':edges,'global':quantile(scores,parameters['target_coverage']),
      'conditional':[quantile(x,parameters['target_coverage']) for x in by_bin],
      'calibration_rows':len(scores),'calibration_rows_by_bin':list(map(len,by_bin))}

def row_metrics(row,multiplier,parameters):
    width=multiplier*max(row['spread'],parameters['spread_floor'])
    low=max(0,row['mean']-width);high=max(0,row['mean']+width);y=row['observed']
    alpha=1-parameters['target_coverage']
    score=high-low+(2/alpha)*(max(0,low-y)+max(0,y-high))
    return (float(low<=y<=high),high-low,score)

def summarize(rows,model,parameters):
    out={}
    for method in ['global','conditional']:
        values=[]
        for r in rows:
            multiplier=model['global'] if method=='global' else model['conditional'][bisect.bisect_right(model['edges'],r['mean'])]
            values.append(row_metrics(r,multiplier,parameters))
        out[method]={'coverage':statistics.mean(x[0] for x in values),'mean_width':statistics.mean(x[1] for x in values),
          'mean_interval_score':statistics.mean(x[2] for x in values)}
    return out

def run(plan):
    p=plan['parameters'];rows=[]
    with gzip.open('input.csv.gz','rt',newline='') as f:
        for r in csv.DictReader(f):
            row={'date':r['date'],'station':r['station'],'group':r['calibration_group'],
              'mean':float(r['mean_mm_day']),'spread':float(r['spread_mm_day']),'observed':float(r['observed_mm_day'])}
            if not all(math.isfinite(row[x]) for x in ['mean','spread','observed']) or row['spread']<0 or row['observed']<0:raise ValueError('Invalid qualified row')
            rows.append(row)
    model=fit(rows,p)
    evaluation=[r for r in rows if r['group']=='evaluation' and p['evaluation_start']<=r['date']<=p['evaluation_end']]
    if not evaluation:raise ValueError('No held-out evaluation rows')
    high=[r for r in evaluation if r['mean']>=model['edges'][-1]]
    stations=sorted(set(r['station'] for r in evaluation));by_station=[]
    for station in stations:
        subset=[r for r in high if r['station']==station]
        if len(subset)<p['minimum_high_rows_per_station']:
            by_station.append({'station':station,'high_rows':len(subset),'eligible':False});continue
        by_station.append({'station':station,'high_rows':len(subset),'eligible':True,**summarize(subset,model,p)})
    eligible=[x for x in by_station if x['eligible']]
    if len(eligible)<p['minimum_evaluation_stations']:raise ValueError('Insufficient high-flow station coverage; no station substitution allowed')
    score_global=statistics.mean(x['global']['mean_interval_score'] for x in eligible)
    score_conditional=statistics.mean(x['conditional']['mean_interval_score'] for x in eligible)
    coverage_global=statistics.mean(x['global']['coverage'] for x in eligible)
    coverage_conditional=statistics.mean(x['conditional']['coverage'] for x in eligible)
    improvement=1-score_conditional/score_global
    rng=random.Random(p['bootstrap_seed']);samples=[]
    for _ in range(p['bootstrap_replicates']):
        sample=rng.choices(eligible,k=len(eligible))
        samples.append(1-statistics.mean(x['conditional']['mean_interval_score'] for x in sample)/statistics.mean(x['global']['mean_interval_score'] for x in sample))
    interval=[quantile(samples,.025),quantile(samples,.975)]
    passed=(improvement>=p['minimum_score_improvement'] and abs(coverage_conditional-p['target_coverage'])<=p['maximum_coverage_error'] and interval[0]>0)
    return {'adapter':'streamflow','model':model,'evaluation_rows':len(evaluation),'high_predicted_flow_rows':len(high),
      'high_predicted_flow_threshold_mm_day':model['edges'][-1],'by_station':by_station,
      'primary':{'equal_station_interval_score_improvement':improvement,'equal_station_global_coverage':coverage_global,
        'equal_station_conditional_coverage':coverage_conditional,'cluster_bootstrap_95_interval':interval,'success_rule_passed':passed},
      'secondary_all_evaluation_rows':summarize(evaluation,model,p),
      'limitations':['Stations are held out from posthoc calibration only, not original LSTM training.',
        'Temporal and spatial dependence invalidate an exchangeable conformal coverage guarantee.',
        'Catchment bootstrap does not account for cross-catchment climate dependence; only 12 selected stations.',
        'Observed-flow missingness may be seasonal; analysis is conditional on recorded nonnegative observations.',
        'No new model, operational flood recommendation, causal explanation or universal extreme-flow claim.']}

if __name__=='__main__':print(json.dumps(run(json.load(open(sys.argv[1]))),sort_keys=True))
