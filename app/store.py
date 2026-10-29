import sqlite3,json,time,uuid,os,socket
from .config import DATA,MODE,REDIS_URL
class Store:
 def __init__(self):
  self.redis=None
  if MODE=='redis':
   import redis
   self.redis=redis.Redis.from_url(REDIS_URL,decode_responses=True,socket_timeout=3,socket_connect_timeout=3)
  self.path=DATA/'store.db'
  if not self.redis:
   with self.db() as c:
    c.execute('CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY,v TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY,stage TEXT,run TEXT,lease REAL DEFAULT 0)')
 def db(self):
  c=sqlite3.connect(self.path,timeout=10);c.execute('PRAGMA journal_mode=WAL');return c
 def get(self,k,default=None):
  if self.redis:v=self.redis.get(k)
  else:
   with self.db() as c:r=c.execute('SELECT v FROM kv WHERE k=?',(k,)).fetchone();v=r[0] if r else None
  return json.loads(v) if v is not None else default
 def set(self,k,v):
  s=json.dumps(v,ensure_ascii=True)
  if self.redis:self.redis.set(k,s)
  else:
   with self.db() as c:c.execute('INSERT OR REPLACE INTO kv VALUES (?,?)',(k,s))
 def enqueue(self,stage,run):
  if self.redis:
   self.redis.zadd('queue:'+stage,{run:time.time()})
  else:
   with self.db() as c:c.execute('INSERT INTO jobs(stage,run) VALUES (?,?)',(stage,run))
 def claim(self,stage):
  now=time.time(); lease=now+60
  if self.redis:
   script="local x=redis.call('ZRANGEBYSCORE',KEYS[1],'-inf',ARGV[1],'LIMIT',0,1); if #x==0 then return nil end; redis.call('ZADD',KEYS[1],ARGV[2],x[1]); return x[1]"
   r=self.redis.eval(script,1,'queue:'+stage,now,lease);return (r,r) if r else None
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE')
   r=c.execute('SELECT id,run FROM jobs WHERE stage=? AND lease<? ORDER BY id LIMIT 1',(stage,now)).fetchone()
   if r:c.execute('UPDATE jobs SET lease=? WHERE id=?',(lease,r[0]))
   return r
 def ack(self,stage,key):
  if self.redis:self.redis.zrem('queue:'+stage,key)
  else:
   with self.db() as c:c.execute('DELETE FROM jobs WHERE id=?',(key,))
 def rate(self,client,limit):
  key='rate:'+client+':'+str(int(time.time()//60))
  if self.redis:
   n=self.redis.incr(key);self.redis.expire(key,120);return n<=limit
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT v FROM kv WHERE k=?',(key,)).fetchone();n=(json.loads(r[0]) if r else 0)+1
   c.execute('INSERT OR REPLACE INTO kv VALUES (?,?)',(key,json.dumps(n)));return n<=limit
 def keys(self,prefix):
  if self.redis:return list(self.redis.scan_iter(prefix+'*'))
  with self.db() as c:return [r[0] for r in c.execute('SELECT k FROM kv WHERE k LIKE ?',(prefix+'%',))]
 def breaker_failure(self,key):
  now=time.time()
  if self.redis:
   lua="local v=redis.call('GET',KEYS[1]); local b={failures=0,open_until=0}; if v then b=cjson.decode(v) end; b.failures=b.failures+1; if b.failures>=2 then b.open_until=tonumber(ARGV[1])+15 end; redis.call('SET',KEYS[1],cjson.encode(b)); return cjson.encode(b)"
   return json.loads(self.redis.eval(lua,1,key,now))
  with self.db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT v FROM kv WHERE k=?',(key,)).fetchone();b=json.loads(row[0]) if row else {'failures':0,'open_until':0};b['failures']+=1
   if b['failures']>=2:b['open_until']=now+15
   c.execute('INSERT OR REPLACE INTO kv VALUES (?,?)',(key,json.dumps(b)));return b
 def event(self,run,event):
  from .telemetry import tracer,STEP_LATENCY,TOKENS,COST
  from opentelemetry import trace
  with tracer.start_as_current_span(event['step'],attributes={'run.id':run,'agent':event.get('agent','unknown'),'step.latency_seconds':float(event.get('latency',0))}) as span:
   context=span.get_span_context();event['trace_id']=format(context.trace_id,'032x');event['span_id']=format(context.span_id,'016x')
  agent=event.get('agent','unknown');STEP_LATENCY.labels(agent,event['step']).observe(float(event.get('latency',0)))
  for kind in ('prompt_tokens','completion_tokens'):
   if event.get(kind) is not None:TOKENS.labels(agent,kind).inc(event[kind])
  if event.get('cost_usd') is not None:COST.labels(agent).inc(event['cost_usd'])
  event.update(run_id=run,time=time.time(),process_id=os.getpid(),service_instance=socket.gethostname())
  self.set('event:'+run+':'+uuid.uuid4().hex,event)
  if os.getenv('LOG_PASSAGES','1')=='1':print(json.dumps(event,ensure_ascii=True),flush=True)
  else:print(json.dumps({k:v for k,v in event.items() if k!='passages'},ensure_ascii=True),flush=True)
 def trace(self,run):return sorted([self.get(k) for k in self.keys('event:'+run+':')],key=lambda x:x['time'])
store=Store()
