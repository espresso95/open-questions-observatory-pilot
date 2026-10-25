"""Build a private, allowlisted disclosure bundle from checked records. No upload."""
import json
import shutil
import zipfile
from pathlib import Path
from .common import ROOT,PRIVATE,now,read_json,write_json,digest,canonical
from .policy import bundle_manifest,validate_question
from .experiment import verify_frozen
from .assessment import assess

REPRODUCE='''import hashlib,json,subprocess,uuid
from pathlib import Path
directory=Path(__file__).resolve().parent
manifest=json.loads((directory/'artifacts.sha256.json').read_text())
for name,h in manifest.items():
 if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=h:raise ValueError('Changed artifact: '+name)
tag='oqo-reproduce-'+uuid.uuid4().hex[:12]
plan=json.loads((directory/'plan.json').read_text())
subprocess.run(['docker','build','--network','none','-t',tag,str(directory)],check=True)
name='oqo-run-'+uuid.uuid4().hex[:12]
try:
 p=subprocess.run(['docker','run','--name',name,'--rm','--network','none','--read-only','--user','65534:65534','--cap-drop','ALL','--security-opt','no-new-privileges','--memory',str(plan['resources']['memory_mib'])+'m','--cpus','1','--pids-limit','32','--tmpfs','/tmp:rw,noexec,nosuid,size=8m','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONHASHSEED=0',tag,'python','entry.py'],capture_output=True,text=True,check=True,timeout=plan['resources']['wall_seconds'])
 observed=json.loads(p.stdout.splitlines()[-1])['results']
 expected=json.loads((directory/'results.json').read_text())
 if observed!=expected:raise ValueError('Reproduction differs')
 print('PASS: every structured result reproduced. This is not scientific peer review.')
finally:subprocess.run(['docker','rm','-f',name],capture_output=True)
'''

def run():
    target=PRIVATE/'next-release-bundle'
    if target.exists():raise ValueError('Review bundle already exists; preserve it and choose a versioned destination before regenerating')
    target.mkdir();index=read_json(PRIVATE/'next-steps/experiment-index.json');questions=[];sources={}
    for path in sorted((PRIVATE/'discovery/questions').glob('Q-*.json')):
        q=read_json(path);assess(q)
        for evidence in q['source_evidence']:
            record=read_json(PRIVATE/'discovery/fulltext'/(evidence['source_id']+'.json'));snapshot=record['snapshot']
            sources[evidence['source_id']]={'id':evidence['source_id'],'title':evidence['title'],'url':evidence['url'],
              'source_sha256':evidence['source_sha256'],'text_sha256':evidence['text_sha256'],
              'retrieved_at':snapshot['retrieved_at'],'extraction':record.get('extraction'),
              'rights':{'analyze':True,'export':True,'license':snapshot.get('source_license_text') or snapshot['rights']['license'],
                'scope':'Metadata, citation and brief necessary quotation only; original full text excluded'}}
            evidence.pop('text_path',None)
        q['run_ids']=[];q['statuses']['validation']='unreviewed'
        q['assessment']['dispatch_eligible']=all(q['assessment']['gates'].values())
        if q['id']=='Q-MATH-002':
            q['run_ids']=['R-'+Path(index['prefix']).name[:12]];q['report_run_id']=q['run_ids'][0]
            q['statuses'].update(research='completed',validation='computationally_reproduced')
            q['outcome_summary']='Nine finite row witnesses found beyond n=100; 513 symmetric certificates and 37 proper-group obstructions independently checked. The general conjecture remains unresolved.'
        if q['id']=='Q-GEO-001':
            q['run_ids']=['R-'+Path(index['streamflow_original']).name[:12],'R-'+Path(index['streamflow']).name[:12]];q['report_run_id']=q['run_ids'][-1]
            q['statuses'].update(research='inconclusive',validation='computationally_reproduced',feasibility='data_blocked')
            q['assessment']['prior_assessment']={'score':q['assessment']['score'],'dispatch_eligible':True,'reason':'Inputs were computationally usable, but station support for the primary endpoint was overestimated'}
            q['assessment']['dispatch_eligible']=False;q['assessment']['gates']['validation_defined']=False
            q['assessment']['blockers']=['Only 3 of 12 fixed evaluation stations meet the frozen high-flow support rule; 8 required. A different future protocol needs fresh justification and freeze.']
            q['outcome_summary']='Inconclusive: the frozen primary-endpoint support requirement failed. No thresholds were lowered and no stations were substituted. Original failures and a diagnostic-only reporting amendment are retained.'
        validate_question(q);questions.append(q)
        write_json(target/'catalog/questions'/q['id']/'question.json',q)
    write_json(target/'catalog/sources-next.json',list(sources.values()))
    for name in ['screening-ledger.json','extraction-audit.json']:
        source=PRIVATE/('discovery' if name.startswith('screening') else 'next-steps')/name
        write_json(target/'catalog/discovery'/name,read_json(source))
    searches=[{'id':'literature-batch'+str(i),'queries':read_json(PRIVATE/f'discovery/literature-batch{i}.json')['queries'],'checked_at':'2026-10-25','coverage':'Web search; structured source assessments are in question records. Raw copyrighted search extracts are excluded.'} for i in range(1,5)]
    write_json(target/'catalog/discovery/search-log.json',searches)
    write_json(target/'site/src/content/questions-v2.json',{'questions':questions})
    for adapter in ('prefix','streamflow'):
        directory=PRIVATE/index[adapter];plan=verify_frozen(directory);result=read_json(directory/'run-primary.json')
        if not read_json(directory/'reproduction.json')['results_identical']:raise ValueError('Unreproduced export')
        identifier='R-'+directory.name[:12];out=target/'research'/identifier;out.mkdir(parents=True)
        for p in (directory/'context').iterdir():shutil.copy2(p,out/p.name)
        for name in ['freeze.json','question.json','run-primary.json','run-fresh-reproduction.json','reproduction.json','independent-verification.json']:
            shutil.copy2(directory/name,out/name)
        write_json(out/'results.json',result['results']);write_json(out/'validation.json',{'reproduction':read_json(directory/'reproduction.json'),'independent_check':read_json(directory/'independent-verification.json'),'external_scientific_review':False,'human_scientific_review':False,'novelty_certified':False})
        if adapter=='prefix':
            verifier="import json\nfrom pathlib import Path\ndata=json.loads(Path(__file__).with_name('results.json').read_text())\n"+(PRIVATE/'next-steps/verify-prefix-independent.py').read_text()
            (out/'independent.py').write_text(verifier)
            shutil.copy2(PRIVATE/'runtime-wheels/requirements.txt',out/'independent-requirements.txt')
        else:
            verifier=(PRIVATE/'next-steps/verify-streamflow-independent.py').read_text()
            verifier=verifier.replace('from engine.common import PRIVATE,read_json,write_json,now','import json\nfrom datetime import datetime,timezone\ndef read_json(p):return json.loads(Path(p).read_text())\ndef now():return datetime.now(timezone.utc).isoformat()')
            verifier=verifier.replace("p=PRIVATE/read_json(PRIVATE/'next-steps/experiment-index.json')['streamflow']","p=Path(__file__).resolve().parent")
            verifier=verifier.replace("p/'context/plan.json'","p/'plan.json'").replace("p/'run-primary.json'","p/'run-primary.json'").replace("p/'context/input.csv.gz'","p/'input.csv.gz'")
            verifier=verifier.replace("write_json(p/'independent-verification.json',receipt);print(receipt)","print(json.dumps(receipt,sort_keys=True))")
            (out/'independent.py').write_text(verifier)
            (out/'independent-requirements.txt').write_text('numpy==2.3.5\n')
        if adapter=='streamflow':
            old=PRIVATE/index['streamflow_original'];prior=out/'prior-attempt';prior.mkdir()
            for p in (old/'context').iterdir():shutil.copy2(p,prior/p.name)
            for name in ['freeze.json','run-primary.json','run-fresh-reproduction.json','run-failure-diagnosis.json']:shutil.copy2(old/name,prior/name)
            write_json(out/'data-manifest.json',read_json(PRIVATE/'datasets/streamflow/qualification.json'))
            write_json(out/'data-rights.json',read_json(PRIVATE/'datasets/streamflow/acquisition.json')['rights'])
        report=(PRIVATE/'next-steps/reports'/(adapter+'.md')).read_text()
        (out/'report.md').write_text(report);(out/'reproduce.py').write_text(REPRODUCE)
        (out/'CITATION.cff').write_text('cff-version: 1.2.0\nmessage: "AI-assisted research pilot; no external scientific review."\ntitle: '+json.dumps(next(q['title'] for q in questions if q.get('report_run_id')==identifier))+'\nauthors:\n  - name: "Open Questions Observatory pilot"\nversion: "'+identifier+'"\n')
        write_json(out/'artifacts.sha256.json',{p.relative_to(out).as_posix():digest(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()})
        public=target/'site/public/data/v2'/identifier;public.mkdir(parents=True)
        for name in ['results.json','plan.json','validation.json']:shutil.copy2(out/name,public/name)
        front='---\ntitle: '+json.dumps(next(q['title'] for q in questions if q.get('report_run_id')==identifier))+'\ndescription: "A bounded AI-assisted investigation with a frozen protocol and retained limitations."\nquestion_id: '+plan['question_id']+'\nrun_id: '+identifier+'\ndisciplines: ['+('mathematics' if adapter=='prefix' else 'geophysics')+']\n---\n\n'
        destination=target/'site/src/content/reports'/(identifier+'.md');destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(front+report)
        zip_path=target/'site/public/downloads'/(identifier+'-reproduction.zip');zip_path.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(out.rglob('*')):
                if p.is_file():
                    info=zipfile.ZipInfo(p.relative_to(out).as_posix(),date_time=(2026,10,25,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
    (target/'docs').mkdir();shutil.copy2(ROOT/'docs/next-steps.md',target/'docs/next-steps.md')
    manifest=bundle_manifest(target);write_json(target/'manifest.json',manifest)
    write_json(PRIVATE/'next-steps/disclosure-candidate.json',{'directory':str(target),'sha256':manifest['sha256'],'files':len(manifest['files']),'human_disclosure_approval':False,'scope':'Ten source-backed cards, two additional pilot reports, complete frozen reproductions and prior failures, derived CC-BY-4.0 data, no source full texts/private state/design/user review details'})
    print('Private disclosure candidate',manifest['sha256'],len(manifest['files']),'files')

if __name__=='__main__':run()
