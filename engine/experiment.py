"""Shared frozen-plan, isolated execution and reproduction interface."""
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from .common import ROOT,PRIVATE,now,canonical,digest,read_json,write_json
from .assessment import admit
from .isolation import docker,CONTEXT

ENTRY='''import json,resource,time,analysis
start=time.monotonic()
with open('plan.json') as f:plan=json.load(f)
result=analysis.run(plan)
r=resource.getrusage(resource.RUSAGE_SELF)
print(json.dumps({'results':result,'resource':{'wall_seconds':time.monotonic()-start,'user_cpu_seconds':r.ru_utime,'system_cpu_seconds':r.ru_stime,'peak_rss_kib':r.ru_maxrss}},sort_keys=True))
'''

def freeze(question,adapter,parameters,resources,input_path=None,amendment=None):
    admit(question)
    if adapter not in ('prefix','streamflow'):raise ValueError('Unregistered research adapter')
    if adapter=='streamflow':
        from .input_support import streamflow
        support=streamflow(input_path,parameters)
        if not support['qualified']:raise ValueError('Prospective input-support gate failed: '+json.dumps(support,sort_keys=True))
    code=(ROOT/'engine/adapters'/f'{adapter}.py').read_bytes()
    data=Path(input_path).read_bytes() if input_path else None
    runtime=read_json(ROOT/'config/runtime.json')['image']
    plan={'schema_version':'2.0','question_id':question['id'],'question_sha256':digest(canonical(question)),
      'adapter':adapter,'adapter_sha256':digest(code),'entry_sha256':digest(ENTRY.encode()),
      'input_sha256':digest(data) if data is not None else None,'runtime':runtime,
      'frozen_at':now(),'parameters':parameters,'resources':resources,
      'policy':{'network':'none','publication':'private_draft','credentials':False,'variants':'Only parameter variants explicitly enumerated here','result_selection':'Retain every attempted row and failure; no tuning after observation'}}
    if amendment:plan['amendment']=amendment
    h=digest(canonical(plan));directory=PRIVATE/'experiments'/h;directory.mkdir(parents=True,exist_ok=False)
    context=directory/'context';context.mkdir();write_json(context/'plan.json',plan);write_json(directory/'question.json',question)
    (context/'analysis.py').write_bytes(code);(context/'entry.py').write_text(ENTRY)
    if data is not None:(context/'input.csv.gz').write_bytes(data)
    (context/'Dockerfile').write_text(f'FROM {runtime}\nWORKDIR /work\nCOPY . /work\nUSER 65534:65534\n')
    write_json(directory/'freeze.json',{'plan_sha256':h,'frozen_at':plan['frozen_at'],'files':{p.name:digest(p.read_bytes()) for p in sorted(context.iterdir())},'outcomes_examined_before_freeze':bool(amendment),'prior_outcome_scope':amendment.get('outcomes_observed') if amendment else None})
    print('FROZEN',adapter,h,flush=True)
    return directory

def verify_frozen(directory):
    directory=Path(directory);freeze=read_json(directory/'freeze.json');context=directory/'context'
    if digest((context/'plan.json').read_bytes())!=freeze['plan_sha256']:raise ValueError('Frozen plan modified')
    if {p.name for p in context.iterdir()}!=set(freeze['files']):raise ValueError('Frozen execution context changed')
    for name,h in freeze['files'].items():
        if digest((context/name).read_bytes())!=h:raise ValueError('Frozen input/code modified: '+name)
    return read_json(context/'plan.json')

def execute(directory,label):
    directory=Path(directory);plan=verify_frozen(directory);context=directory/'context'
    receipt_path=directory/('run-'+label+'.json')
    if receipt_path.exists():raise ValueError('Run labels are immutable')
    tag='oqo-'+directory.name[:16]+':frozen';name='oqo-'+uuid.uuid4().hex[:12]
    started=now();t=time.monotonic();isolation=None
    try:
        docker('build','--network','none','-t',tag,str(context),timeout=90)
        r=plan['resources']
        docker('create','--name',name,'--network','none','--read-only','--user','65534:65534',
          '--cap-drop','ALL','--security-opt','no-new-privileges','--memory',str(r['memory_mib'])+'m','--cpus','1',
          '--pids-limit','32','--tmpfs','/tmp:rw,noexec,nosuid,size=8m','--ulimit','fsize=8192:8192',
          '-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONHASHSEED=0',tag,'python','entry.py')
        info=json.loads(docker('inspect',name))[0];host=info['HostConfig']
        isolation={'network':host['NetworkMode'],'read_only':host['ReadonlyRootfs'],'user':info['Config']['User'],
          'privileged':host['Privileged'],'host_binds':host['Binds'],'mounts':info['Mounts'],'cap_drop':host['CapDrop'],
          'memory_bytes':host['Memory'],'pids_limit':host['PidsLimit']}
        if isolation['network']!='none' or not isolation['read_only'] or isolation['user']!='65534:65534' or isolation['privileged'] or isolation['host_binds'] or isolation['mounts']:raise ValueError('Isolation contract failed')
        raw=docker('start','--attach',name,timeout=r['wall_seconds'])
        if len(raw.encode())>r['max_output_bytes']:raise ValueError('Output budget exceeded')
        (directory/('run-'+label+'.jsonl')).write_text(raw)
        lines=raw.splitlines()
        output=json.loads(lines[-1])
        checkpoints=[json.loads(line) for line in lines[:-1]]
        if any(x.get('event')!='checkpoint' for x in checkpoints):raise ValueError('Unexpected adapter output')
        receipt={'plan_sha256':directory.name,'label':label,'started_at':started,'completed_at':now(),
          'outcome':'completed','isolation':isolation,'checkpoint_count':len(checkpoints),'results_sha256':digest(canonical(output['results'])),**output}
    except Exception as e:
        partial=getattr(e,'output',None)
        if partial:
            partial=partial.decode(errors='replace') if isinstance(partial,bytes) else partial
            (directory/('run-'+label+'-partial.jsonl')).write_text(partial[:plan['resources']['max_output_bytes']])
        receipt={'plan_sha256':directory.name,'label':label,'started_at':started,'completed_at':now(),
          'outcome':'failed','isolation':isolation,'error_type':type(e).__name__,'error':str(e)[:1000],
          'stderr':str(getattr(e,'stderr',''))[:4000]}
    finally:
        subprocess.run(['docker','--context',CONTEXT,'rm','-f',name],capture_output=True,timeout=15)
    receipt['host_elapsed_seconds']=round(time.monotonic()-t,4);write_json(receipt_path,receipt)
    print('RUN',label,receipt['outcome'],receipt['host_elapsed_seconds'],flush=True)
    return receipt

def reproduce(directory):
    a=execute(directory,'primary');b=execute(directory,'fresh-reproduction')
    same=a['outcome']==b['outcome']=='completed' and a['results_sha256']==b['results_sha256']
    receipt={'verified_at':now(),'fresh_containers':True,'results_identical':same,
      'primary_hash':a.get('results_sha256'),'reproduction_hash':b.get('results_sha256'),
      'scientific_review':False,'independent_implementation':False}
    write_json(Path(directory)/'reproduction.json',receipt)
    return a,b,receipt
