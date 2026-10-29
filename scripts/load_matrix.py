"""Run from the project folder on a Docker host; every load generator is a container."""
import subprocess,json,argparse,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def command(args,log):
 result=subprocess.run(['docker','compose',*args],cwd=ROOT,text=True,capture_output=True)
 log.write(result.stdout+result.stderr);log.flush()
 if result.returncode and not (result.returncode==1 and 'locust' in args):raise RuntimeError('Compose command failed; inspect '+log.name)
def run(workers,users,seconds,cache=True):
 label=f'w{workers}_u{users}_cache{int(cache)}';env=ROOT/'.env';lines=env.read_text().splitlines();lines=[x for x in lines if not x.startswith('RETRIEVAL_CACHE=')];lines.append('RETRIEVAL_CACHE='+str(int(cache)));env.write_text('\n'.join(lines)+'\n')
 with (ROOT/'evidence'/('bench_'+label+'.log')).open('w') as log:
  command(['up','-d','--no-build','--scale',f'agent-worker={workers}'],log)
  command(['--profile','test','run','--rm','--no-deps','-e','BENCH_LABEL='+label,'-e','BENCH_WARMUP=10','loadtest','locust','-f','scripts/locustfile.py','--headless','--host',read_env('LOAD_HOST'),'--users',str(users),'--spawn-rate',str(users),'--run-time',str(seconds)+'s','--stop-timeout','65','--csv','/service/evidence/bench_'+label],log)
 result=json.loads((ROOT/'evidence'/('bench_'+label+'.json')).read_text());result.update(workers=workers,users=users,retrieval_cache=cache);print(json.dumps(result),flush=True);return result
def read_env(key):
 return next(x.split('=',1)[1] for x in (ROOT/'.env').read_text().splitlines() if x.startswith(key+'='))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=45);p.add_argument('--cases',default='1:1,1:10,1:20,1:30,3:10,3:30,3:60');args=p.parse_args();rows=[]
 for case in args.cases.split(','):
  workers,users=map(int,case.split(':'));rows.append(run(workers,users,args.seconds))
 for cache in [False,True]:rows.append(run(3,1,30,cache))
 (ROOT/'evidence/load_matrix.json').write_text(json.dumps({'declared_slo_seconds':30,'measurement':'Locust E2E with 0.5 second model stub, 10 second warmup and graceful draining','rows':rows},indent=2))
