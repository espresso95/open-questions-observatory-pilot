import json
import subprocess
import time
import uuid
from .common import PRIVATE, ROOT, digest, read_json, write_json

CONTEXT = 'colima-oqopilot'

def docker(*args, timeout=120):
    return subprocess.run(['docker', '--context', CONTEXT, *args], check=True,
                          capture_output=True, text=True, timeout=timeout).stdout

def pin_image():
    path = ROOT / 'config/runtime.json'
    if path.exists(): return read_json(path)['image']
    image = json.loads(docker('image', 'inspect', 'python:3.14-slim'))[0]['RepoDigests'][0]
    write_json(path, {'image':image, 'context':CONTEXT, 'network':'none',
                      'memory_bytes':134217728, 'cpu_limit':1, 'wall_seconds':45,
                      'dependencies':'Python standard library only; no runtime package installation'})
    return image

def run_container(image, command):
    name = 'oqo-' + uuid.uuid4().hex[:12]
    started = time.monotonic()
    try:
        output = docker('run', '--name', name, '--rm', '--network', 'none', '--read-only',
                        '--user', '65534:65534', '--cap-drop', 'ALL',
                        '--security-opt', 'no-new-privileges', '--memory', '128m',
                        '--cpus', '1', '--pids-limit', '32', '--ulimit', 'fsize=8192:8192',
                        '--tmpfs', '/tmp:rw,noexec,nosuid,size=8m',
                        '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'PYTHONHASHSEED=0',
                        image, *command, timeout=45)
        if len(output.encode()) > 1_000_000: raise ValueError('Output budget exceeded')
        return json.loads(output), round(time.monotonic()-started, 4)
    finally:
        subprocess.run(['docker','--context',CONTEXT,'rm','-f',name], capture_output=True, timeout=10)

def inspect_isolation(image):
    code = '''import json,os,socket,pathlib
out={"uid":os.getuid(),"host_home_absent":not pathlib.Path("/Users/mottbot").exists(),"docker_socket_absent":not pathlib.Path("/var/run/docker.sock").exists(),"credential_env_absent":not any(k for k in os.environ if any(s in k for s in ("TOKEN","SECRET","KEY","CREDENTIAL")))}
try:
 open("/forbidden-write","w").write("probe")
 out["root_write_denied"]=False
except OSError: out["root_write_denied"]=True
try:
 socket.create_connection(("1.1.1.1",443),timeout=1)
 out["external_network_denied"]=False
except OSError: out["external_network_denied"]=True
out["interfaces"]=os.listdir("/sys/class/net")
print(json.dumps(out))'''
    r, elapsed = run_container(image, ['python','-I','-B','-c',code])
    if not (r['uid'] == 65534 and r['interfaces'] == ['lo'] and
            all(r[k] for k in ('host_home_absent','docker_socket_absent','credential_env_absent',
                               'root_write_denied','external_network_denied'))):
        raise ValueError('Isolation probe failed')
    return dict(r, elapsed_seconds=elapsed)

def run_analysis(plan, manifest):
    image = pin_image()
    stage = PRIVATE / 'staging' / digest(json.dumps(plan, sort_keys=True).encode())[:16]
    stage.mkdir(parents=True, exist_ok=True)
    (stage/'analysis.py').write_bytes((ROOT/'engine/analysis.py').read_bytes())
    write_json(stage/'plan.json', plan)
    for source_id, name in [('D-NINO34','nino34.data')]:
        (stage/name).write_bytes((PRIVATE / manifest[source_id]['raw_path']).read_bytes())
    (stage/'Dockerfile').write_text('FROM '+image+'\nWORKDIR /inputs\nCOPY analysis.py plan.json nino34.data /inputs/\nUSER 65534:65534\n')
    tag = 'oqo-pilot:' + digest((stage/'plan.json').read_bytes())[:16]
    docker('build', '--network=none', '--pull=false', '-t', tag, str(stage), timeout=120)
    r1, elapsed1 = run_container(tag, ['python','-I','-B','/inputs/analysis.py'])
    r2, elapsed2 = run_container(tag, ['python','-I','-B','/inputs/analysis.py'])
    if r1 != r2: raise ValueError('Fresh reproduction mismatch')
    image_id = json.loads(docker('image','inspect',tag))[0]['Id']
    return r1, {'fresh_container_reproduction':True, 'identical_structured_outputs':True,
                'analysis_image_id':image_id, 'base_image':image,
                'run_seconds':[elapsed1,elapsed2], 'isolation':inspect_isolation(image),
                'review_type':'automated_computational_checks', 'external_scientific_review':False}
