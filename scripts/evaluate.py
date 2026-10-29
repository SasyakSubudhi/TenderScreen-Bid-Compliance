import json,time,statistics,os,uuid
from pathlib import Path
from app.engine import execute
from app.config import ROOT
from app.store import store
def evaluate(version):
 rows=[]
 for case in json.loads((ROOT/'eval/scenarios.json').read_text()):
  run='eval-'+version+'-'+case['id']+'-'+uuid.uuid4().hex[:8];started=time.perf_counter();r=execute(case['bid'],run=run,prompt=version)
  cited={c['id'] for c in r['citations']};required=set(case['expected_citations']);resolved=sum(cid in cited for f in r['findings'] for cid in f['citation_ids']);total=sum(len(f['citation_ids']) for f in r['findings'])
  # Equivalent explicit reference-based scorer for this finite domain, no LLM judge.
  groundedness=resolved/total if total else 0
  context={p['id'] for event in store.trace(run) if isinstance(event.get('passages'),list) for p in event['passages']}
  relevance=len(context&required)/len(context) if context else 0
  faithful=float(r['route']==case['expected_route'] and required.issubset(cited) and r['verification']['passed'])
  hallucination=(total-resolved)/total if total else 0
  rows.append({'id':case['id'],'run_id':run,'route':r['route'],'expected':case['expected_route'],'groundedness':groundedness,'context_relevance':relevance,'faithfulness':faithful,'hallucination_rate':hallucination,'verification_passed':r['verification']['passed'],'latency_seconds':time.perf_counter()-started,'basis':r['basis'],'retrieved_context_ids':sorted(context)})
 metrics={k:statistics.mean(x[k] for x in rows) for k in ['groundedness','context_relevance','faithfulness','hallucination_rate']};metrics['route_accuracy']=statistics.mean(x['route']==x['expected'] for x in rows)
 return {'prompt_version':version,'mode':os.getenv('PROVIDER_MODE','stub'),'reference_scorer':'finite-contract expected routes and citations; not an independent legal judgement','metrics':metrics,'scenarios':rows}
if __name__=='__main__':
 result={'before':evaluate('v1'),'after':evaluate('v2'),'change':'v2 explicitly searches modifying policy clauses and follows clause identifiers; v1 searches tender only','limitations':'Reference metrics measure this finite screen; they are not independent semantic judgement or model generalisation.'}
 out=ROOT/'evidence'/os.getenv('EVAL_OUTPUT','evaluation.json');out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(result,indent=2));print(json.dumps({k:v['metrics'] for k,v in result.items() if isinstance(v,dict)},indent=2))
