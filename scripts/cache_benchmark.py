import time,json,statistics
from app.engine import corpus
from app.config import ROOT
def p95(x):return sorted(x)[min(len(x)-1,int(len(x)*.95))]
rows={}
for enabled in [False,True]:
 samples=[]
 for _ in range(200):
  if not enabled:corpus.cache.clear()
  start=time.perf_counter();corpus.search('startup turnover experience relaxation','policy');samples.append(time.perf_counter()-start)
 rows['warm' if enabled else 'cold']={'p95_seconds':p95(samples),'p50_seconds':statistics.median(samples),'provider_cost_usd':0.0}
rows['scope']='retrieval microbenchmark only; full-run p95 cache effect requires Compose load test. Hash embeddings and stub have zero provider charges.'
(ROOT/'evidence/cache.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
