"""Trusted second-machine verifier; only approved analysis executes inside Docker."""
import hashlib
import io
import json
import math
import platform
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen
from .common import ROOT,now,read_json,write_json

URL='https://espresso95.github.io/open-questions-observatory-pilot/downloads/oqo-pilot-reproduction.zip'

def compare(expected,observed,path='',differences=None):
    differences=[] if differences is None else differences
    if isinstance(expected,bool) or expected is None or isinstance(expected,str):
        if expected!=observed:raise ValueError('Categorical mismatch: '+path)
    elif isinstance(expected,(int,float)):
        if not isinstance(observed,(int,float)) or not math.isfinite(observed) or not math.isclose(expected,observed,abs_tol=1e-10,rel_tol=1e-10):
            raise ValueError('Numerical mismatch: '+path)
        differences.append(abs(expected-observed))
    elif isinstance(expected,list):
        if not isinstance(observed,list) or len(expected)!=len(observed):raise ValueError('List mismatch: '+path)
        for i,(a,b) in enumerate(zip(expected,observed)):compare(a,b,path+f'/{i}',differences)
    else:
        if not isinstance(observed,dict) or set(expected)!=set(observed):raise ValueError('Object mismatch: '+path)
        for k in expected:compare(expected[k],observed[k],path+'/'+k,differences)
    return differences

def main():
    approval=read_json(ROOT/'manifest.json')
    expected_zip=approval['files']['site/public/downloads/oqo-pilot-reproduction.zip']
    with urlopen(URL,timeout=30) as response:raw=response.read(2_000_001)
    if len(raw)>2_000_000 or hashlib.sha256(raw).hexdigest()!=expected_zip:raise ValueError('Unapproved downloaded package')
    prefix='research/R-37cd1717a83c/'
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        files={name:archive.read(prefix+name) for name in ('analysis.py','plan.json','nino34.data','results.json','artifacts.sha256.json')}
    checks=json.loads(files['artifacts.sha256.json'])
    for name in ('analysis.py','plan.json','nino34.data','results.json'):
        if hashlib.sha256(files[name]).hexdigest()!=checks[name]:raise ValueError('Artifact hash mismatch')
    plan=json.loads(files['plan.json']);image=read_json(ROOT/'config/runtime.json')['image']
    if plan['base_image']!=image:raise ValueError('Unexpected runtime')
    def docker(*args,timeout=120):
        return subprocess.check_output(['docker',*args],text=True,timeout=timeout)
    docker('pull',image)
    with tempfile.TemporaryDirectory() as temporary:
        p=Path(temporary)
        for name in ('analysis.py','plan.json','nino34.data'):(p/name).write_bytes(files[name])
        (p/'Dockerfile').write_text('FROM '+image+'\nCOPY analysis.py plan.json nino34.data /inputs/\nUSER 65534:65534\n')
        tag='oqo-second-machine:'+plan['analysis_sha256'][:12]
        docker('build','--network=none','--pull=false','-t',tag,str(p))
        raw_result=docker('run','--rm','--network','none','--read-only','--user','65534:65534',
          '--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--cpus','1','--pids-limit','32',
          tag,'python','-I','-B','/inputs/analysis.py',timeout=45)
    differences=compare(json.loads(files['results.json']),json.loads(raw_result))
    record={'verified_at':now(),'package_url':URL,'package_sha256':expected_zip,
      'host':platform.platform(),'architecture':platform.machine(),
      'run_id':'R-37cd1717a83c','numeric_absolute_tolerance':1e-10,'numeric_relative_tolerance':1e-10,
      'maximum_numeric_difference':max(differences),'numeric_values_checked':len(differences),
      'categorical_outputs_identical':True,'research_container_network':'none',
      'host_mounts':False,'research_executed_unprivileged':True,'scientific_review':False}
    write_json(ROOT/'output/second-machine-reproduction.json',record)
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
