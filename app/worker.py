import os,time,json,threading
from prometheus_client import start_http_server,Counter,Histogram,Gauge
from .telemetry import tracer,carrier,extract
from .store import store
from .engine import initial,research,verify
from .config import RUN_TIMEOUT
from .quality import live_score
import socket
ROLE=os.getenv('WORKER_ROLE','research')
TASKS=Counter('agent_tasks_total','Agent tasks',['agent','outcome']);LAT=Histogram('agent_task_seconds','Agent latency',['agent'],buckets=(.1,.5,1,2,5,10,20,30,45,60))
UP=Gauge('agent_uptime_seconds','Worker uptime',['agent']);HEART=Gauge('agent_last_heartbeat_seconds','Heartbeat',['agent']);CALLS=Counter('agent_tools_total','Tool calls',['agent']);STEPS=Counter('agent_steps_total','Steps',['agent']);RETRY=Counter('agent_retries_total','Model retries',['agent'])
def process_one(role=ROLE):
 job=store.claim(role)
 if not job:return False
 key,run=job;record=store.get('run:'+run)
 if record is None:store.ack(role,key);return True
 if record['status']=='completed' or (role=='research' and record['status']=='verifying'):store.ack(role,key);return True
 t=time.perf_counter()
 try:
  with tracer.start_as_current_span(role,context=extract(record.get('trace_context',{})),attributes={'run.id':run,'correlation.id':run}):
   if time.time()-record['submitted_at']>RUN_TIMEOUT:raise TimeoutError('End to end run deadline exceeded')
   record['status']='researching' if role=='research' else 'verifying';store.set('run:'+run,record)
   if role=='research':
    state=initial(run,record['bid'],record['prompt_version']);state['started']=record['submitted_at'];state=research(state);store.set('state:'+run,state);record['status']='verifying';record['trace_context']=carrier();store.set('run:'+run,record);store.enqueue('verification',run)
   else:
    state=verify(store.get('state:'+run));record['result']=state['result'];record['status']='completed';record['completed_at']=time.time();record['latency_seconds']=record['completed_at']-record['submitted_at']
    if record['latency_seconds']>RUN_TIMEOUT:raise TimeoutError('Run deadline exceeded during verification')
    events=store.trace(run);costs=[x.get('cost_usd') for x in events if x['step']=='model'];record['cost_usd']=sum(costs) if all(x is not None for x in costs) else None
    if int(run[:8],16)%5==0:record['quality']=live_score(record['result'],record['bid'],events)
    store.set('run:'+run,record)
   TASKS.labels(role,'success').inc()
 except Exception as e:
  record.update(status='completed',completed_at=time.time(),latency_seconds=time.time()-record['submitted_at'],result={'route':'seek-clarification','human_review':True,'basis':'Run incomplete: '+str(e),'findings':[],'citations':[],'authority':'screening recommendation only','prompt_version':record['prompt_version'],'verification':{'passed':False},'escalation_path':{'owner':'Tender committee','action':'Retry after service recovery'}});store.set('run:'+run,record);TASKS.labels(role,'failure').inc();store.event(run,{'agent':role,'step':'failure','error':str(e)})
 if record.get('status')=='completed' and 'quality' not in record and int(run[:8],16)%5==0:
  record['quality']=live_score(record['result'],record['bid'],store.trace(run));store.set('run:'+run,record)
 events=[e for e in store.trace(run) if e.get('agent')==role];STEPS.labels(role).inc(len(events));CALLS.labels(role).inc(sum(e['step']=='tool' for e in events));RETRY.labels(role).inc(sum(e.get('attempt',1)>1 for e in events));LAT.labels(role).observe(time.perf_counter()-t);store.ack(role,key);return True
def main():
 start=time.time();start_http_server(int(os.getenv('WORKER_METRICS_PORT','9100')))
 while True:
  UP.labels(ROLE).set(time.time()-start);HEART.labels(ROLE).set(time.time());store.set('heartbeat:'+ROLE+':'+socket.gethostname()+':'+str(os.getpid()),time.time())
  if not process_one():time.sleep(.1)
if __name__=='__main__':main()
