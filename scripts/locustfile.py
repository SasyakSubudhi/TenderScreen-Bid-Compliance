import json,time,os,uuid
from pathlib import Path
from locust import HttpUser,task,between,events
import gevent
MEASUREMENT_STARTED=float('inf')
@events.test_start.add_listener
def begin(environment,**kwargs):
 def reset():
  global MEASUREMENT_STARTED
  environment.stats.reset_all();MEASUREMENT_STARTED=time.time()
 gevent.spawn_later(float(os.getenv('BENCH_WARMUP','0')),reset)
@events.test_stop.add_listener
def save_summary(environment,**kwargs):
 label=os.getenv('BENCH_LABEL')
 if not label:return
 stat=environment.stats.get('complete_screening_run','E2E');elapsed=max(.001,time.time()-MEASUREMENT_STARTED)
 data={'label':label,'warmup_seconds':float(os.getenv('BENCH_WARMUP','0')),'measured_seconds_including_drain':elapsed,'e2e_attempts':stat.num_requests,'completed_runs':stat.num_requests-stat.num_failures,'failed_runs':stat.num_failures,'completed_rps':(stat.num_requests-stat.num_failures)/elapsed,'attempt_rps':stat.num_requests/elapsed,'p50_seconds':stat.get_response_time_percentile(.5)/1000 if stat.num_requests else None,'p95_seconds':stat.get_response_time_percentile(.95)/1000 if stat.num_requests else None,'slo_seconds':30,'slo_met':bool(stat.num_requests and stat.get_response_time_percentile(.95)<=30000 and not stat.num_failures),'scope':'E2E from submission through terminal verification; includes queue and polling'}
 (Path(__file__).resolve().parents[1]/'evidence'/('bench_'+label+'.json')).write_text(json.dumps(data,indent=2))
SAMPLE=json.loads((Path(__file__).resolve().parents[1]/'examples/valid.json').read_text())
class ScreenUser(HttpUser):
 wait_time=between(.1,.3)
 @task
 def screen(self):
  start=time.perf_counter();started_wall=time.time();error=None
  headers={'Authorization':'Bearer '+os.getenv('API_TOKEN','')}
  try:
   # Unique bidder name defeats whole-run memoisation; retrieval cache remains realistic.
   body={**SAMPLE,'bidder_name':'Load '+uuid.uuid4().hex}
   response=self.client.post('/v1/runs',json=body,headers=headers,name='submit');response.raise_for_status();run=response.json()['run_id']
   while time.perf_counter()-start<65:
    status=self.client.get('/v1/runs/'+run,headers=headers,name='poll').json()
    if status.get('status')=='completed':
     if not status['result']['verification']['passed']:raise RuntimeError('incomplete or unverified result')
     break
    time.sleep(.2)
   else:raise TimeoutError('run not terminal within 65 seconds')
  except Exception as e:error=e
  if started_wall>=MEASUREMENT_STARTED:events.request.fire(request_type='E2E',name='complete_screening_run',response_time=(time.perf_counter()-start)*1000,response_length=0,exception=error,context={})
