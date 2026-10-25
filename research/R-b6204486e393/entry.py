import json,resource,time,analysis
start=time.monotonic()
with open('plan.json') as f:plan=json.load(f)
result=analysis.run(plan)
r=resource.getrusage(resource.RUSAGE_SELF)
print(json.dumps({'results':result,'resource':{'wall_seconds':time.monotonic()-start,'user_cpu_seconds':r.ru_utime,'system_cpu_seconds':r.ru_stime,'peak_rss_kib':r.ru_maxrss}},sort_keys=True))
