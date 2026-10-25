import hashlib,json,subprocess,uuid
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
