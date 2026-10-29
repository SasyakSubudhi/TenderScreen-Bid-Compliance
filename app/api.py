import json,os,time,uuid,hashlib
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse,FileResponse,Response
from fastapi.exceptions import RequestValidationError
from prometheus_client import generate_latest,CONTENT_TYPE_LATEST
from .contracts import Bid,Feedback
from .store import store
from .config import ROOT,DATA,PROMPT
from .guardrails import inspect
from .telemetry import tracer,carrier
app=FastAPI(title='TenderScreen',version='1.0.0',description='Closed tender summary screening. Committee retains all decisions.')
@app.middleware('http')
async def boundary(request,call_next):
 if request.url.path.startswith('/v1'):
  token=os.getenv('API_TOKEN','')
  if token and request.headers.get('Authorization')!='Bearer '+token:return JSONResponse({'detail':'authentication required'},401)
  # X-Client-ID is authenticated by a gateway in production. Peer address is the demo fallback.
  client=hashlib.sha256((request.headers.get('Authorization') or (request.client.host if request.client else 'local')).encode()).hexdigest()
  if request.method=='POST' and not store.rate(client,int(os.getenv('RATE_LIMIT','60'))):return JSONResponse({'detail':'client rate limit exceeded'},429,headers={'Retry-After':'60'})
  if len(await request.body())>65536:return JSONResponse({'detail':'body exceeds 64 KiB'},413)
 with tracer.start_as_current_span(request.method+' '+request.url.path):
  response=await call_next(request)
  return response
@app.exception_handler(RequestValidationError)
async def quarantine(request,exc):
 q=uuid.uuid4().hex;errors=json.loads(json.dumps(exc.errors(),default=str));store.set('quarantine:'+q,{'time':time.time(),'path':request.url.path,'errors':errors,'body_sha256':hashlib.sha256(await request.body()).hexdigest()})
 return JSONResponse({'quarantine_id':q,'errors':errors,'agent_started':False},422)
@app.get('/')
def client():return FileResponse(ROOT/'web/index.html')
@app.get('/health')
def health():
 store.set('health',time.time());return {'status':'ok','store':os.getenv('STORE_MODE','sqlite'),'prompt':PROMPT}
@app.get('/metrics')
def metrics():
 runs=[store.get(k) for k in store.keys('run:')];completed=[r for r in runs if r['status']=='completed'];lat=[r.get('latency_seconds',0) for r in completed]
 text=generate_latest().decode()+f'pipeline_runs_total {len(runs)}\npipeline_completed_total {len(completed)}\npipeline_escalations_total {sum(r.get("result",{}).get("route")=="seek-clarification" for r in completed)}\n'
 for bound in [.1,.5,1,2,5,10,20,30,45,60,float('inf')]:
  label='+Inf' if bound==float('inf') else str(bound);text+=f'pipeline_run_seconds_bucket{{le="{label}"}} {sum(x<=bound for x in lat)}\n'
 text+=f'pipeline_run_seconds_count {len(lat)}\npipeline_run_seconds_sum {sum(lat)}\n'
 if (DATA/'index_manifest.json').exists():
  m=json.loads((DATA/'index_manifest.json').read_text());text+=f'corpus_chunks {m["chunks"]}\ncorpus_built_timestamp_seconds {m["built_at"]}\ncorpus_ingest_chunks_per_second {m["chunks_per_second"]}\n'
 return Response(text,media_type=CONTENT_TYPE_LATEST)
@app.post('/v1/runs',status_code=202)
def submit(bid:Bid):
 body=bid.model_dump();flags=inspect(body)
 if flags:
  q=uuid.uuid4().hex;store.set('quarantine:'+q,{'time':time.time(),'errors':flags,'body_sha256':hashlib.sha256(json.dumps(body).encode()).hexdigest()});return JSONResponse({'quarantine_id':q,'errors':flags,'agent_started':False},422)
 run=uuid.uuid4().hex;record={'run_id':run,'status':'queued','bid':body,'submitted_at':time.time(),'prompt_version':PROMPT,'trace_context':carrier()};store.set('run:'+run,record);store.enqueue('research',run)
 return {'run_id':run,'status':'queued','poll_path':'/v1/runs/'+run,'correlation_id':run}
@app.get('/v1/runs/{run_id}')
def status(run_id:str):
 r=store.get('run:'+run_id)
 if r is None:raise HTTPException(404,'unknown run')
 # Reconcile a lost worker without presenting a confident answer.
 if r['status']!='completed' and time.time()-r['submitted_at']>60:
  r.update(status='completed',latency_seconds=time.time()-r['submitted_at'],result={'route':'seek-clarification','human_review':True,'basis':'Worker heartbeat or deadline lost. Run incomplete.','citations':[],'findings':[],'prompt_version':r['prompt_version'],'verification':{'passed':False}});store.set('run:'+run_id,r)
 return r
@app.get('/v1/runs/{run_id}/trace')
def trace(run_id:str):
 status(run_id);return {'run_id':run_id,'events':store.trace(run_id)}
@app.post('/v1/runs/{run_id}/feedback',status_code=201)
def feedback(run_id:str,body:Feedback):
 r=status(run_id)
 if r['status']!='completed':raise HTTPException(409,'run not completed')
 store.set('feedback:'+run_id,{'run_id':run_id,**body.model_dump(),'time':time.time()});return {'saved':True}
@app.get('/v1/dashboard')
def dashboard():
 runs=[store.get(k) for k in store.keys('run:')];feedback=[store.get(k) for k in store.keys('feedback:')];completed=[r for r in runs if r['status']=='completed']
 return {'runs':len(runs),'completed':len(completed),'quarantined':len(store.keys('quarantine:')),'feedback':{'count':len(feedback),'satisfactory':sum(f['satisfactory'] for f in feedback)},'quality_over_time':[{'time':r.get('completed_at',r['submitted_at']),'score':r['quality']['citation_resolution'],**r['quality']} for r in sorted(completed,key=lambda r:r['submitted_at']) if 'quality' in r][-30:],'heartbeats':{k:store.get(k) for k in store.keys('heartbeat:')}}
