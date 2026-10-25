"""One-shot orchestration; no autonomous scheduler or model API is implied."""
import argparse
import shutil
import sqlite3
from pathlib import Path
from .common import ROOT, PRIVATE, canonical, digest, now, read_json, write_json
from .broker import acquire, evidence, validate_evidence
from .isolation import pin_image, run_analysis
from .policy import validate_question, validate_sources, bundle_manifest

def connection():
    PRIVATE.mkdir(exist_ok=True)
    db = sqlite3.connect(PRIVATE/'state.sqlite3')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, time TEXT, kind TEXT, entity TEXT, detail TEXT);
      CREATE TABLE IF NOT EXISTS source_versions(id TEXT, hash TEXT, record TEXT, PRIMARY KEY(id,hash));
      CREATE TABLE IF NOT EXISTS question_versions(id TEXT, hash TEXT, record TEXT, PRIMARY KEY(id,hash));
      CREATE TABLE IF NOT EXISTS plans(hash TEXT PRIMARY KEY, record TEXT);
      CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, plan_hash TEXT, status TEXT, results_hash TEXT);
    ''')
    return db

def event(db, kind, entity, detail):
    db.execute('INSERT INTO events(time,kind,entity,detail) VALUES(?,?,?,?)',(now(),kind,entity,detail))
    db.commit()

def prepare():
    manifest = acquire()
    sources = {s['id']:s for s in manifest}
    validate_sources(manifest)
    item = evidence(sources['S-PAPER'],
        'These results suggest that incorporating additional ocean-atmosphere variables may help transcend SPB limitations and advance long-range ENSO prediction.',
        'Abstract, final sentence; normalized text character offsets retained privately')
    validate_evidence(item,sources)
    experiment = read_json(ROOT/'config/experiment.json')
    image = pin_image()
    plan = dict(experiment, inputs={'nino34.data':sources['D-NINO34']['sha256']},
                analysis_sha256=digest((ROOT/'engine/analysis.py').read_bytes()), base_image=image,
                literature_search_sha256=digest((ROOT/'config/literature-search.json').read_bytes()))
    # Idempotent freeze: reruns reuse the original timestamp, never overwrite a changed plan.
    identity = digest(canonical(plan))
    path = PRIVATE/'plans'/f'{identity}.json'
    if path.exists(): plan = read_json(path)
    else:
        plan.update(frozen_at=now(),registration='Internal timestamped protocol; not external preregistration')
        write_json(path,plan)
    plan_hash = digest(canonical(plan))
    write_json(PRIVATE/'current-plan.json',plan)
    write_json(PRIVATE/'current-evidence.json',item)
    db=connection()
    for s in manifest:
        db.execute('INSERT OR IGNORE INTO source_versions VALUES(?,?,?)',(s['id'],s['sha256'],canonical(s).decode()))
    db.execute('INSERT OR IGNORE INTO plans VALUES(?,?)',(plan_hash,canonical(plan).decode()))
    db.commit()
    event(db,'plan_frozen','Q-ENSO-001',plan_hash)
    print('Frozen plan:',plan_hash,plan['frozen_at'],flush=True)
    return plan,sources,item

def assessment(validation):
    ratings={'input_readiness':4,'validation_readiness':3,'local_compute_fit':4,'question_precision':4,'implementation_readiness':4}
    weights={'input_readiness':30,'validation_readiness':25,'local_compute_fit':20,'question_precision':15,'implementation_readiness':10}
    return {'rubric_version':'1.0','ratings':ratings,'weights':weights,
            'score':sum(weights[k]*v/4 for k,v in ratings.items()),
            'meaning':'Heuristic readiness score; not a probability of success or correctness',
            'dispatch_eligible':True,'blockers':[],
            'evidence':{'input_readiness':'NOAA format, units, rights and content hash checked',
                        'validation_readiness':'Temporal holdout, paired block uncertainty, residual check and clean reproduction; few climate cycles and revised data are limitations',
                        'local_compute_fit':validation['run_seconds'],
                        'question_precision':'Frozen exact six-month metric and comparator contract',
                        'implementation_readiness':'Small standard-library adapter with bounded container resources'},
            'hardware':{'host_architecture':'arm64','vm_profile':'oqopilot','vm_cpu_count':2,'vm_memory_gib':2}}

def report(plan,r,validation):
    scores=r['scores']['spring_initialized']
    rows='\n'.join(f"| {label} | {scores[key]['rmse']:.4f} | {scores[key]['mae']:.4f} | {scores[key]['n']} |" for key,label in [('persistence','Persistence'),('ar6','Non-seasonal AR6'),('seasonal_ar6','Season-aware AR6')])
    comparisons=[]
    for key,label in [('persistence','persistence'),('ar6','non-seasonal AR6')]:
        c=r['primary_comparisons'][key]
        comparisons.append(f"Against {label}, relative RMSE skill is {100*c['rmse_skill']:.2f}%. Positive values favor the season-aware model.")
        for ci in c['intervals']:
            comparisons.append(f"- {ci['block_years']}-year blocks: descriptive 95% interval {100*ci['lower_95']:.2f}% to {100*ci['upper_95']:.2f}%.")
    answer=('The frozen decision rule was met for this bounded retrospective comparison.' if r['claim_supported_under_frozen_rule'] else
            'The frozen decision rule was not met. This pilot does not demonstrate the proposed robust improvement; the general research question remains open.')
    return f'''---
title: "Can calendar information improve spring ENSO forecasts?"
description: "A frozen, reproducible pilot on a question with no answer located in the documented search."
---
# Can calendar information improve spring ENSO forecasts?

{answer}

This is a retrospective research pilot, with no answer to the exact comparison located in the documented English-language search. Seasonal ENSO forecasting is well studied; neither a new forecasting algorithm nor independent novelty is claimed. The wider spring predictability barrier is unresolved by this experiment.

## Question and motivation

Does a fixed season-aware direct six-month AR6 forecast lower February–April initialized Niño 3.4 RMSE by at least 5% against both persistence and an otherwise comparable non-seasonal AR6, with positive paired intervals under all prespecified block lengths?

Gan and colleagues' [2026 preprint](https://arxiv.org/html/2601.02050v1) identifies persistent seasonal forecast limitations and suggests richer predictor information. This pilot tests a narrower statistical question about calendar effects. It does not reproduce their deep-learning model or test their physical-variable proposal. [Related 2026 work](https://www.sciencedirect.com/science/article/pii/S0169207026001019) already studies seasonal score-driven forecasts through 2024; its methods, index vintage, inputs and evaluation window differ. Full-text access to that study failed, limiting the literature assessment.

## Data and fixed method

Use [NOAA CPC ERSSTv5 monthly Niño 3.4 anomalies](https://psl.noaa.gov/data/timeseries/month/Nino34_CPC/) in °C relative to 1981–2010. The cached snapshot has {r['input_months']} valid months, from {r['first_input']} through {r['last_input']}. No missing values were imputed.

Training uses {r['training_examples']} examples with target months ending by {r['last_training_target']}. Holdout forecasts start in {r['first_test_issue']}; the last available issue is {r['last_test_issue']}, targeting {r['last_test_target']}. At each issue date the model sees only that month's anomaly and the preceding five months. Forecasts are direct six-month forecasts; parameters are fitted once and never updated from holdout outcomes.

Both regressions use a fixed ridge penalty of 1 on all coefficients except the intercept. The season-aware model adds sine/cosine of issue month and their interactions with the latest anomaly. No hyperparameter search or subsequent outcome-driven model changes occurred. Persistence predicts the latest observed anomaly. Two fitted models and one fixed baseline are the entire analysis family.

The plan was frozen internally at {plan['frozen_at']}; it is not an external preregistration. This is pseudo-out-of-sample evaluation of a single revised data vintage. Historical release delays and data revisions are not reconstructed, so it is not an operational forecast verification.

## Primary results

The primary subset comprises forecasts initialized in February, March or April, with only targets available by the September 2026 cutoff. This operational definition differs from some published spring-barrier definitions.

| Forecast | RMSE (°C) | MAE (°C) | Forecasts |
|---|---:|---:|---:|
{rows}

{'\n\n'.join(comparisons)}

The prespecified rule requires at least 5% lower RMSE against both baselines and a positive lower skill endpoint for every 2-, 3- and 4-year paired circular block bootstrap. It does not require a favorable result to count the pilot as a completed investigation. Secondary all-month and other-month results and every prediction are in results.json.

## Validation and limits

The identical structured output was reproduced in two fresh Linux containers from a digest-pinned Python image. Each run had a 45-second wall limit, 128 MiB memory, one CPU, no network, no host mounts, a read-only root filesystem and an unprivileged user. Runs took {validation['run_seconds'][0]:.3f} and {validation['run_seconds'][1]:.3f} seconds. Probes checked root write denial, external network denial, missing host home/socket and absence of credential environment variables.

Bootstrap uncertainty uses paired circular blocks of calendar years, 2,000 replicates per block length and fixed seeds. There are few ENSO cycles; the intervals are descriptive finite-record uncertainty and can miss slower dependence or nonstationarity. The frozen 5% threshold is an engineering decision rule, not a physical discovery threshold. No test here establishes future forecast skill or causation.

Computational reproduction checks repeatability. It does not establish scientific adequacy. No independent scientist, expert reviewer or external peer reviewer has reviewed this pilot. Publication remains a private draft pending human disclosure approval.

## Reproduction and attribution

Download the reproducibility package from this page. It contains the exact data snapshot, plan, source code, pinned runtime, results, checksums, literature search and reproduction command. Full source-paper HTML, private logs and SQLite are excluded.

Data: NOAA Climate Prediction Center; provided by NOAA Physical Sciences Laboratory, Boulder, Colorado, USA. The source paper is Gan et al., arXiv:2601.02050v1 (CC BY 4.0). This report and analysis are AI-assisted, with no endorsement by NOAA or the paper's authors.
'''

def run():
    plan,sources,item=prepare()
    plan_hash=digest(canonical(plan))
    run_id='R-'+plan_hash[:12]
    db=connection()
    previous=db.execute('SELECT status FROM runs WHERE id=?',(run_id,)).fetchone()
    output=PRIVATE/'runs'/run_id
    output.mkdir(parents=True,exist_ok=True)
    if previous and previous[0]=='completed':
        result=read_json(output/'results.json'); validation=read_json(output/'validation.json')
        event(db,'idempotent_run_reused',run_id,plan_hash)
    else:
        db.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?,?)',(run_id,plan_hash,'running',None));db.commit()
        event(db,'run_started',run_id,plan_hash)
        try:
            result,validation=run_analysis(plan,sources)
            write_json(output/'results.json',result);write_json(output/'validation.json',validation)
        except Exception as e:
            db.execute('UPDATE runs SET status=? WHERE id=?',('failed',run_id));db.commit()
            event(db,'run_failed',run_id,str(e));raise
        db.execute('UPDATE runs SET status=?,results_hash=? WHERE id=?',('completed',digest(canonical(result)),run_id));db.commit()
        event(db,'run_completed',run_id,digest(canonical(result)))
    q={'schema_version':'1.0','id':'Q-ENSO-001',
       'title':'Can calendar information improve six-month spring ENSO forecasts?',
       'scope':{'system':'Niño 3.4 monthly SST anomaly, 5N–5S / 170–120W',
                'claim':plan['claim'],'parent_problem':'ENSO spring predictability barrier',
                'relationship':'Bounded agent-formulated follow-up, motivated by source; not a verbatim author question',
                'data_window':'Train targets through 2014; holdout issue dates 2015 onward, observed targets through 2026-09'},
       'disciplines':['climate-science','statistics'],'source_evidence':[item],
       'statuses':{'literature':'no_answer_found','feasibility':'pilot_ready',
                   'research':'completed' if result['claim_supported_under_frozen_rule'] else 'inconclusive',
                   'validation':'computationally_reproduced','publication':'private_draft'},
       'resolved':False,'literature_search':read_json(ROOT/'config/literature-search.json'),
       'assessment':assessment(validation),'run_ids':[run_id], 'created_at':plan['frozen_at']}
    validate_question(q)
    db.execute('INSERT OR IGNORE INTO question_versions VALUES(?,?,?)',(q['id'],digest(canonical(q)),canonical(q).decode()));db.commit()
    export(q,plan,result,validation,sources,run_id)
    print('Pilot result:',result['disposition'],flush=True)

def export(q,plan,result,validation,sources,run_id):
    target=ROOT/'review-bundle'
    if target.exists(): shutil.rmtree(target)
    research=target/'research'/run_id
    research.mkdir(parents=True)
    write_json(target/'catalog/questions/Q-ENSO-001/question.json',q)
    public_sources=[]
    for s in sources.values():
        public_sources.append({k:v for k,v in s.items() if k not in ('raw_path','text_path')})
    write_json(target/'catalog/sources.json',public_sources)
    for name,value in [('plan.json',plan),('results.json',result),('validation.json',validation),
                       ('literature-search.json',q['literature_search'])]:
        write_json(research/name,value)
    (research/'report.md').write_text(report(plan,result,validation))
    shutil.copy2(ROOT/'engine/analysis.py',research/'analysis.py')
    shutil.copy2(PRIVATE/sources['D-NINO34']['raw_path'],research/'nino34.data')
    write_json(research/'data-manifest.json',{'dataset':next(s for s in public_sources if s['id']=='D-NINO34'),
                                           'changes':'None; exact downloaded snapshot retained'})
    write_json(research/'environment.lock',read_json(ROOT/'config/runtime.json'))
    (research/'reproduce.sh').write_text('''#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m engine.reproduce_package
''')
    # Standalone package runner avoids host mounts; copies exact approved files into an image.
    (research/'reproduce.py').write_text((ROOT/'engine/reproduce.py').read_text())
    (research/'reproduce.sh').write_text('#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\npython3 reproduce.py\n')
    (research/'CITATION.cff').write_text('cff-version: 1.2.0\nmessage: "AI-assisted pilot; private draft; no external scientific review."\ntitle: "Can calendar information improve spring ENSO forecasts?"\nauthors:\n  - name: "Open Questions Observatory pilot"\ndate-released: "2026-10-25"\nversion: "'+run_id+'"\n')
    (research/'references.bib').write_text('@misc{gan2026, title={Explore the Ideology of Deep Learning in ENSO Forecasts}, author={Gan, Yanhai and others}, year={2026}, eprint={2601.02050}, archivePrefix={arXiv}}\n@misc{noaa, title={Niño 3.4 SST Index from NOAA ERSST V5}, author={{NOAA CPC and NOAA PSL}}, url={https://psl.noaa.gov/data/timeseries/month/Nino34_CPC/}, note={Snapshot retrieved 2026-10-25}}\n')
    checks={p.name:digest(p.read_bytes()) for p in sorted(research.iterdir()) if p.is_file()}
    write_json(research/'artifacts.sha256.json',checks)
    independent=PRIVATE/'runs'/run_id/'independent-verification.json'
    if independent.exists(): shutil.copy2(independent,research/'independent-verification.json')
    figures=PRIVATE/'runs'/run_id/'figures'
    if figures.exists():
        shutil.copytree(figures,research/'figures')
        public_figures=ROOT/'site/public/figures'
        public_figures.mkdir(parents=True,exist_ok=True)
        for f in figures.iterdir(): shutil.copy2(f,public_figures/f.name)
    checks={p.relative_to(research).as_posix():digest(p.read_bytes()) for p in sorted(research.rglob('*')) if p.is_file() and p.name!='artifacts.sha256.json'}
    write_json(research/'artifacts.sha256.json',checks)
    manifest=bundle_manifest(target)
    write_json(target/'manifest.json',manifest)
    write_json(PRIVATE/'current-run.json',{'run_id':run_id,'plan_sha256':digest(canonical(plan)),
                                         'bundle_sha256':manifest['sha256']})
    site=ROOT/'site'
    content=site/'src/content/reports'
    content.mkdir(parents=True,exist_ok=True)
    for old in content.glob('*.md'): old.unlink()
    shutil.copy2(research/'report.md',content/f'{run_id}.md')
    data=site/'public/data/v1'
    data.mkdir(parents=True,exist_ok=True)
    write_json(data/'catalog.json',[q]);write_json(data/'results.json',result)
    write_json(data/'validation.json',validation);write_json(data/'plan.json',plan)
    write_json(data/'sources.json',public_sources)
    write_json(data/'manifest.json',dict(manifest,build_time=now(),record_count=1,run_id=run_id))
    write_json(site/'src/content/pilot.json',{'question':q,'result':result,'validation':validation,
                                            'run_id':run_id,'manifest':manifest,'plan':plan})
    downloads=site/'public/downloads'
    downloads.mkdir(parents=True,exist_ok=True)
    shutil.make_archive(str(downloads/'oqo-pilot-reproduction'),'zip',target)
    print('Private review bundle:',manifest['sha256'],flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','run'])
    args=parser.parse_args()
    if args.command=='prepare': prepare()
    else: run()
