"""Independent numerical checks and figures; does not tune or alter the experiment."""
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'.private/matplotlib'))
import numpy as np
import jsonschema
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .common import ROOT, PRIVATE, canonical, digest, now, read_json, write_json
from .broker import validate_evidence
from .policy import validate_question, validate_sources, bundle_manifest

def main():
    current=read_json(PRIVATE/'current-run.json')
    run=PRIVATE/'runs'/current['run_id']
    result=read_json(run/'results.json')
    plan=read_json(PRIVATE/'current-plan.json')
    sources={s['id']:s for s in read_json(PRIVATE/'acquisition.json')}
    question=read_json(ROOT/'review-bundle/catalog/questions/Q-ENSO-001/question.json')
    jsonschema.Draft202012Validator(read_json(ROOT/'schemas/question.schema.json'),format_checker=jsonschema.FormatChecker()).validate(question)
    validate_question(question);validate_sources(sources.values())
    for item in question['source_evidence']: validate_evidence(item,sources)
    assert digest(canonical(plan))==current['plan_sha256']
    assert digest((ROOT/'engine/analysis.py').read_bytes())==plan['analysis_sha256']
    assert digest((PRIVATE/sources['D-NINO34']['raw_path']).read_bytes())==plan['inputs']['nino34.data']
    # Separate input parsing, feature construction, and LAPACK QR/SVD least-squares.
    dates=[]; values=[]
    for line in (PRIVATE/sources['D-NINO34']['raw_path']).read_text().splitlines():
        fields=line.split()
        if len(fields)!=13 or not fields[0].isdigit() or len(fields[0])!=4: continue
        for m,token in enumerate(fields[1:],1):
            if float(token)>-90: dates.append(f'{int(fields[0]):04d}-{m:02d}');values.append(float(token))
    values=np.array(values)
    indices=np.arange(5,len(values)-6)
    training=[i for i in indices if dates[i]>=plan['train_start'] and dates[i+6]<=plan['train_target_end']]
    testing=[i for i in indices if dates[i]>=plan['test_issue_start'] and dates[i+6]<=plan['data_cutoff']]
    maximum_beta_error=0.; maximum_prediction_error=0.
    for model,seasonal in [('ar6',False),('seasonal_ar6',True)]:
        def x(i):
            base=[1.,*values[i-np.arange(6)]]
            if seasonal:
                a=2*np.pi*(int(dates[i][-2:])-1)/12
                base += [np.sin(a),np.cos(a),values[i]*np.sin(a),values[i]*np.cos(a)]
            return base
        X=np.array([x(i) for i in training]);y=values[np.array(training)+6]
        penalty=np.eye(X.shape[1])*np.sqrt(plan['ridge']);penalty[0,0]=0
        beta=np.linalg.lstsq(np.vstack([X,penalty]),np.r_[y,np.zeros(len(penalty))],rcond=None)[0]
        maximum_beta_error=max(maximum_beta_error,float(np.max(np.abs(beta-np.array(result['parameters'][model])))))
        pred=np.array([x(i) for i in testing])@beta
        saved=np.array([p[model] for p in result['predictions']])
        maximum_prediction_error=max(maximum_prediction_error,float(np.max(np.abs(pred-saved))))
        assert maximum_prediction_error<1e-9
        for subset in ('all','spring_initialized','other_months'):
            mask=np.array([True if subset=='all' else (int(dates[i][-2:]) in [2,3,4])==(subset=='spring_initialized') for i in testing])
            e=pred[mask]-values[np.array(testing)[mask]+6]
            assert abs(float(np.sqrt(np.mean(e**2)))-result['scores'][subset][model]['rmse'])<1e-10
    assert maximum_beta_error<1e-9
    status={'checked_at':now(),'method':'Independent NumPy parsing/features and augmented least-squares (LAPACK), not the experiment normal-equation solver',
            'maximum_coefficient_difference':maximum_beta_error,'maximum_prediction_difference':maximum_prediction_error,
            'question_schema_passed':True,'source_quote_and_hash_checks_passed':True,
            'temporal_split_passed':plan['train_target_end']<plan['test_issue_start'],
            'prose_table_values_generated_from_results':True,'scientific_review':False}
    write_json(run/'independent-verification.json',status)
    figures=run/'figures';figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'#f3f2e9','axes.facecolor':'#f3f2e9','axes.edgecolor':'#899383','text.color':'#223c31','axes.labelcolor':'#223c31'})
    f,ax=plt.subplots(figsize=(8,3.7),layout='constrained')
    models=['persistence','ar6','seasonal_ar6'];labels=['Persistence','Non-seasonal AR6','Season-aware AR6']
    scores=result['scores']['spring_initialized']
    bars=ax.bar(labels,[scores[m]['rmse'] for m in models],color=['#9fae98','#4f7762','#bc573e'],width=.55)
    for bar,m in zip(bars,models): ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.025,f"{scores[m]['rmse']:.3f}",ha='center')
    ax.set(ylim=(0,1.3),ylabel='Six-month forecast RMSE (°C)',title=f"Spring-initialized holdout forecasts (n={scores['ar6']['n']})")
    ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    f.savefig(figures/'primary-rmse.svg');f.savefig(figures/'primary-rmse.png',dpi=180);plt.close(f)
    f,ax=plt.subplots(figsize=(8,4.2),layout='constrained')
    rows=result['predictions'];x=np.arange(len(rows))
    ax.plot(x,[p['observed'] for p in rows],color='#223c31',lw=2,label='Observed anomaly')
    ax.plot(x,[p['ar6'] for p in rows],color='#789179',lw=1,label='Non-seasonal AR6')
    ax.plot(x,[p['seasonal_ar6'] for p in rows],color='#bc573e',lw=1,label='Season-aware AR6')
    ticks=[i for i,p in enumerate(rows) if p['target_date'].endswith('-01')]
    ax.set_xticks(ticks,[rows[i]['target_date'][:4] for i in ticks]);ax.axhline(0,color='#999',lw=.7)
    ax.set(ylabel='Niño 3.4 anomaly (°C)',xlabel='Target month',title='Every six-month holdout forecast, fixed parameters')
    ax.legend(frameon=False,ncol=3,fontsize=8);ax.grid(alpha=.12)
    f.savefig(figures/'holdout-series.svg');f.savefig(figures/'holdout-series.png',dpi=180);plt.close(f)
    print(json.dumps(status,indent=2))

if __name__=='__main__': main()
