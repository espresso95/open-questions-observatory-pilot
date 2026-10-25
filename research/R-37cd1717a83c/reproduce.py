"""Standalone downloaded-package reproduction. Run beside plan.json."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

root=Path(__file__).resolve().parent
def call(*args, timeout=120):
    return subprocess.check_output(['docker',*args],text=True,timeout=timeout)

def main():
    checks=json.loads((root/'artifacts.sha256.json').read_text())
    for name,h in checks.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=h: raise SystemExit('Hash mismatch: '+name)
    plan=json.loads((root/'plan.json').read_text())
    image=plan['base_image']
    call('pull',image)
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)
        for name in ('analysis.py','plan.json','nino34.data'): (p/name).write_bytes((root/name).read_bytes())
        (p/'Dockerfile').write_text('FROM '+image+'\nCOPY analysis.py plan.json nino34.data /inputs/\nUSER 65534:65534\n')
        tag='oqo-reproduce:'+plan['analysis_sha256'][:12]
        call('build','--network=none','-t',tag,str(p))
        raw=call('run','--rm','--network','none','--read-only','--user','65534:65534',
                 '--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m',
                 '--cpus','1','--pids-limit','32',tag,'python','-I','-B','/inputs/analysis.py',timeout=45)
    result=json.loads(raw)
    if result!=json.loads((root/'results.json').read_text()): raise SystemExit('Reproduction mismatch')
    print('PASS: exact structured results reproduced from the downloaded package in a fresh restricted container.')

if __name__=='__main__': main()
