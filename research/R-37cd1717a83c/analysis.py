"""Restricted-container ENSO experiment. Standard library only, no network."""
import hashlib
import json
import math
import random
from pathlib import Path

def load(path):
    rows = []
    missing = 0
    for line in Path(path).read_text().splitlines():
        fields = line.split()
        if len(fields) != 13 or not fields[0].isdigit() or len(fields[0]) != 4:
            continue
        year = int(fields[0])
        for month, token in enumerate(fields[1:], 1):
            v = float(token)
            if not math.isfinite(v): raise ValueError('Non-finite input')
            if v < -90:
                missing += 1
                continue
            if abs(v) > 10: raise ValueError('Implausible temperature anomaly')
            rows.append({'date':f'{year:04d}-{month:02d}', 'year':year, 'month':month,
                         'ordinal':year*12+month, 'value':v})
    if len(rows) < 600: raise ValueError('Insufficient data')
    for a,b in zip(rows,rows[1:]):
        if b['ordinal']-a['ordinal'] != 1: raise ValueError('Duplicate or internal missing month')
    return rows, missing

def features(rows, i, seasonal):
    x = [1.] + [rows[i-j]['value'] for j in range(6)]
    if seasonal:
        angle = 2*math.pi*(rows[i]['month']-1)/12
        s,c = math.sin(angle),math.cos(angle)
        x += [s,c,rows[i]['value']*s,rows[i]['value']*c]
    return x

def solve(matrix, rhs):
    a = [row[:] + [b] for row,b in zip(matrix,rhs)]
    n = len(a)
    for k in range(n):
        p = max(range(k,n), key=lambda j:abs(a[j][k]))
        a[k],a[p] = a[p],a[k]
        if abs(a[k][k]) < 1e-12: raise ValueError('Singular model')
        scale = a[k][k]
        a[k] = [v/scale for v in a[k]]
        for j in range(n):
            if j == k: continue
            scale = a[j][k]
            a[j] = [x-scale*y for x,y in zip(a[j],a[k])]
    return [r[-1] for r in a]

def fit(training, rows, seasonal, ridge):
    xs = [features(rows,i,seasonal) for i in training]
    ys = [rows[i+6]['value'] for i in training]
    n = len(xs[0])
    gram = [[sum(x[j]*x[k] for x in xs) + (ridge if j==k and j else 0) for k in range(n)] for j in range(n)]
    rhs = [sum(x[j]*y for x,y in zip(xs,ys)) for j in range(n)]
    beta = solve(gram,rhs)
    residual = max(abs(sum(a*b for a,b in zip(row,beta))-y) for row,y in zip(gram,rhs))
    if residual > 1e-7: raise ValueError('Linear system validation failed')
    return beta, residual

def metrics(rows, model):
    errors = [r[model]-r['observed'] for r in rows]
    n = len(errors)
    if not n: raise ValueError('Empty evaluation subset')
    return {'n':n,'rmse':math.sqrt(sum(e*e for e in errors)/n),
            'mae':sum(abs(e) for e in errors)/n,'bias':sum(errors)/n}

def skill(rows, baseline):
    return 1-metrics(rows,'seasonal_ar6')['rmse']/metrics(rows,baseline)['rmse']

def bootstrap(rows, baseline, block_years, repeats, seed):
    years = sorted({r['issue_year'] for r in rows})
    by_year = {y:[r for r in rows if r['issue_year']==y] for y in years}
    rng = random.Random(seed)
    values = []
    for _ in range(repeats):
        chosen = []
        while len(chosen) < len(years):
            start = rng.randrange(len(years))
            chosen.extend(years[(start+j)%len(years)] for j in range(block_years))
        sample = [r for y in chosen[:len(years)] for r in by_year[y]]
        values.append(skill(sample,baseline))
    values.sort()
    return {'block_years':block_years,'repetitions':repeats,'seed':seed,
            'lower_95':values[int(.025*repeats)],'upper_95':values[int(.975*repeats)],
            'method':'paired circular calendar-year block bootstrap; descriptive finite-record uncertainty'}

def compute(plan, root='/inputs'):
    root = Path(root)
    for name,h in plan['inputs'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != h:
            raise ValueError('Input hash mismatch')
    rows, missing = load(root/'nino34.data')
    training = [i for i in range(5,len(rows)-6) if rows[i]['date'] >= plan['train_start']
                and rows[i+6]['date'] <= plan['train_target_end']]
    test = [i for i in range(5,len(rows)-6) if plan['test_issue_start'] <= rows[i]['date']
            and rows[i+6]['date'] <= plan['data_cutoff']]
    if not training or len(test)<60: raise ValueError('Insufficient train/test coverage')
    if rows[training[-1]+6]['ordinal'] >= rows[test[0]]['ordinal']:
        raise ValueError('Temporal training/holdout leakage')
    params, residuals = {},{}
    for name,seasonal in [('ar6',False),('seasonal_ar6',True)]:
        params[name],residuals[name] = fit(training,rows,seasonal,plan['ridge'])
    predictions = []
    for i in test:
        r = {'issue_date':rows[i]['date'],'issue_year':rows[i]['year'],
             'issue_month':rows[i]['month'],'target_date':rows[i+6]['date'],
             'observed':rows[i+6]['value'],'persistence':rows[i]['value'],
             'spring_initialized':rows[i]['month'] in plan['primary_issue_months']}
        for name,seasonal in [('ar6',False),('seasonal_ar6',True)]:
            r[name] = sum(x*b for x,b in zip(features(rows,i,seasonal),params[name]))
        predictions.append(r)
    subsets = {'all':predictions,'spring_initialized':[r for r in predictions if r['spring_initialized']],
               'other_months':[r for r in predictions if not r['spring_initialized']]}
    scores = {sub:{m:metrics(rs,m) for m in ('persistence','ar6','seasonal_ar6')} for sub,rs in subsets.items()}
    comparisons = {}
    for baseline in ('persistence','ar6'):
        intervals = [bootstrap(subsets['spring_initialized'],baseline,b,plan['bootstrap_repeats'],plan['seed']+b)
                     for b in plan['bootstrap_block_years']]
        comparisons[baseline] = {'rmse_skill':skill(subsets['spring_initialized'],baseline),
                                 'intervals':intervals}
    supported = all(v['rmse_skill']>=plan['minimum_relative_rmse_improvement']
                    and all(ci['lower_95']>0 for ci in v['intervals']) for v in comparisons.values())
    return {'schema_version':'1.0','question_id':'Q-ENSO-001',
            'claim_supported_under_frozen_rule':supported,
            'disposition':'bounded_support' if supported else 'inconclusive_or_no_demonstrated_advantage',
            'input_months':len(rows),'trailing_missing_values':missing,'first_input':rows[0]['date'],
            'last_input':rows[-1]['date'],'training_examples':len(training),
            'last_training_target':rows[training[-1]+6]['date'],
            'first_test_issue':predictions[0]['issue_date'],'last_test_issue':predictions[-1]['issue_date'],
            'last_test_target':predictions[-1]['target_date'],'scores':scores,
            'primary_comparisons':comparisons,'parameters':params,'solver_residuals':residuals,
            'predictions':predictions,
            'notes':['Retrospective pseudo-out-of-sample analysis using a single currently revised data vintage.',
                     'Not an operational forecast comparison; historical data-release lags and revisions are not reconstructed.',
                     'Primary spring initialization means February–April; this does not equate to every published definition of the spring barrier.',
                     'Few ENSO cycles limit inference; circular block bootstrap intervals are descriptive and not proof of future skill.',
                     'No conclusion about physical causes or resolution of the general spring predictability barrier.']}

if __name__=='__main__':
    plan = json.loads(Path('/inputs/plan.json').read_text())
    print(json.dumps(compute(plan),sort_keys=True,allow_nan=False))
