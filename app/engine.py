import json,time,concurrent.futures,hashlib
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from . import provider
from .config import MAX_STEPS,MAX_TOOLS,RUN_TIMEOUT,CALL_TIMEOUT,PROMPT,ROOT
from .corpus import Corpus
from .guardrails import inspect,safe_output
from .contracts import Decision
from .store import store
corpus=Corpus()
class State(TypedDict,total=False):
 run_id:str
 bid:dict
 prompt_version:str
 phase:int
 retrieved:dict
 done:bool
 started:float
 reason:str
 tool_calls:int
 review_attempt:int
 result:dict
 history:list
def evidence_tool(name,args,bid):
 if name=='corpus_search':return corpus.search(**args)
 if name=='clause_lookup':
  clause=corpus.lookup(**args)
  return [clause] if clause else []
 if name=='request_fields':return {'category':bid['category'],'average_turnover':sum(bid['turnover_inr'])/5,'exemption_claimed':bid['exemption_claimed'],'recognition_id':bid['recognition_id']}
 raise ValueError('tool not allowlisted')
def research_step(s):
 if time.time()-s['started']>RUN_TIMEOUT or s['phase']>=MAX_STEPS or s['tool_calls']>=MAX_TOOLS:
  return {**s,'done':True,'reason':'loop_or_wall_clock_limit'}
 try:
  a=provider.call(s);name=a['tool'];args=a.get('args',{})
  if name in ('request_fields','handoff'):args={}
  if name=='corpus_search':args={k:v for k,v in args.items() if k in ('query','family','k')}
  if name=='clause_lookup':args={k:v for k,v in args.items() if k=='clause_id'}
  if name=='corpus_search' and (not isinstance(args.get('query'),str) or not 1<=len(args['query'])<=500 or type(args.get('k',4)) is not int or not 1<=args.get('k',4)<=10 or args.get('family') not in (None,'tender','policy')):raise ValueError('invalid search tool contract')
  if name=='clause_lookup' and (not isinstance(args.get('clause_id'),str) or not 1<=len(args['clause_id'])<=100):raise ValueError('invalid clause tool contract')
  if name=='handoff':return {**s,'done':True}
  if inspect(args):raise ValueError('unsafe tool arguments')
  start=time.perf_counter();pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
  try:result=pool.submit(evidence_tool,name,args,s['bid']).result(timeout=CALL_TIMEOUT)
  finally:pool.shutdown(wait=False,cancel_futures=True)
  if isinstance(result,list):
   for c in result:s['retrieved'][c['id']]=c
  store.event(s['run_id'],{'agent':'research','step':'tool','tool':name,'query':args,'passages':result,'latency':time.perf_counter()-start,'prompt_version':s['prompt_version'],'cost_usd':0})
  return {**s,'phase':s['phase']+1,'tool_calls':s['tool_calls']+1,'history':s.get('history',[])+[{'tool':name,'args':args}]}
 except Exception as e:return {**s,'done':True,'reason':str(e)[:250]}
g=StateGraph(State);g.add_node('choose_and_call_tool',research_step);g.add_edge(START,'choose_and_call_tool');g.add_conditional_edges('choose_and_call_tool',lambda s:END if s.get('done') else 'choose_and_call_tool');research_graph=g.compile()
def research(s):return research_graph.invoke(s,{'recursion_limit':MAX_STEPS+3})
REQUIRED={'registration','pan','gst','audited_accounts','order_certificates','signed_tender','undertaking','non_debarment','local_content','authorization','fall_clause'}
def draft(s):
 b=s['bid'];r=s['retrieved'];findings=[]
 def finding(condition,status,ids,basis):findings.append({'condition':condition,'status':status,'citation_ids':ids,'basis':basis})
 special=b['category'] in ('startup','mse')
 policy='P-STARTUP' if b['category']=='startup' else 'P-MSE'
 avg=sum(b['turnover_inr'])/5
 for cond,ok,cid,description in [('turnover',avg>=2400000,'T-TURNOVER',f'Five-year average INR {avg:,.2f}; threshold INR 2,400,000.'),('experience',b['eligible_orders']>=5,'T-EXPERIENCE',f"{b['eligible_orders']} eligible implemented orders; threshold five.")]:
  conflict=not ok and special
  finding(cond,'met' if ok else ('conflict' if conflict else 'unmet'),[cid]+([policy] if conflict else []),description+(' Potential policy relaxation requires committee review and technical quality check.' if conflict else ''))
 if b['emd_paid_inr']>=24000:finding('emd','met',['T-EMD'],'Declared payment covers INR 24,000.')
 elif b['exemption_claimed'] and b['category']=='mse' and b['own_goods_or_services']:
  finding('emd','review',['T-EMD'],'MSE exemption claimed with registration; committee must verify certificate and own supply status.')
 elif b['category']=='startup':finding('emd','review',['T-EMD','G-170'],'Startup security exemption needs policy version and recognition review; no automatic adverse recommendation.')
 else:finding('emd','unmet',['T-EMD'],'Declared EMD below INR 24,000 and no supported exemption.')
 missing=sorted(REQUIRED-set(b['documents']))
 finding('documents','review' if missing else 'met',['T-DOCUMENTS','T-ANNEXURES','T-TURNOVER','T-EXPERIENCE'],'Missing declared documents: '+', '.join(missing) if missing else 'All screened document categories declared present; authenticity remains for committee.')
 finding('local_content','met' if b['local_content_percent']>=20 else 'unmet',['T-LOCAL'],f"Declared local content {b['local_content_percent']} percent; minimum 20 percent.")
 finding('technical_quality','review',['T-TECHNICAL'],'Full technical evaluation and authenticity checks are outside this summary screen.')
 uncertain=b['category'] in ('consortium','foreign','unknown') or (special and not b['recognition_id']) or b['technical_compliance']=='unknown'
 conflict=any(f['status']=='conflict' for f in findings)
 if s.get('reason') or uncertain or conflict or missing or any(f['status']=='review' and f['condition']=='emd' for f in findings):route='seek-clarification'
 elif any(f['status']=='unmet' for f in findings):route='reject-with-cited-condition'
 else:route='pass-to-technical-evaluation'
 basis=s.get('reason') or ('Tender and policy may conflict; tender committee must resolve both sources.' if conflict else ('Incomplete or unclear evidence requires committee clarification.' if route=='seek-clarification' else 'Screened summary findings only; tender committee retains every final decision.'))
 # v1 is a deliberately weaker prompt/retrieval baseline. Verification still blocks unsupported citations.
 ids=sorted({x for f in findings for x in f['citation_ids']})
 citations=[r[x] for x in ids if x in r]
 result={'route':route,'human_review':True,'basis':basis,'findings':findings,'citations':citations,'prompt_version':s['prompt_version'],'authority':'screening recommendation only'}
 return result
def verify_result(result,retrieved,bid):
 errors=[];seen={c['id']:c for c in result['citations']}
 for f in result['findings']:
  for cid in f['citation_ids']:
   if cid not in seen or cid not in retrieved:errors.append('unretrieved:'+cid)
   elif seen[cid]!=retrieved[cid] or seen[cid]!=corpus.lookup(cid):errors.append('altered:'+cid)
 # Deterministic entailment check for the finite supported contract, not an LLM judge.
 if result['findings']!=draft({'bid':bid,'retrieved':retrieved,'prompt_version':result['prompt_version']})['findings']:errors.append('unsupported_finding')
 try:safe_output(result['basis']);Decision.model_validate(result)
 except Exception as e:errors.append('output_filter:'+str(e)[:80])
 return errors
def verifier_step(s):
 start=time.perf_counter();result=draft(s)
 if s.get('tamper'):result['findings'][0]['basis']='Invented unsupported threshold'
 errors=verify_result(result,s['retrieved'],s['bid'])
 if s.get('reason'):errors.append('incomplete_research:'+s['reason'])
 store.event(s['run_id'],{'agent':'verification','step':'verification','errors':errors,'verified':not errors,'latency':time.perf_counter()-start,'prompt_version':s['prompt_version'],'cost_usd':0})
 if errors and not s.get('reason') and not s.get('review_attempt') and s['prompt_version']=='v2':
  # Alternate retrieval strategy: exact clause IDs derived from failed verification.
  ids={cid for f in result['findings'] for cid in f['citation_ids']}
  for cid in ids:
   clauses=evidence_tool('clause_lookup',{'clause_id':cid},s['bid'])
   for c in clauses:s['retrieved'][cid]=c
  store.event(s['run_id'],{'agent':'verification','step':'repair_search','query':sorted(ids),'passages':list(s['retrieved'].values()),'cost_usd':0})
  return {**s,'review_attempt':1,'done':False}
 if errors:
  result={'route':'seek-clarification','human_review':True,'basis':'Evidence verification failed. Human review required. '+', '.join(errors),'findings':[],'citations':list(s['retrieved'].values()),'prompt_version':s['prompt_version'],'authority':'screening recommendation only'}
  result['verification']={'passed':False,'errors':errors,'fallback':'no unverified condition findings returned'}
 else:result['verification']={'passed':True,'errors':[]}
 result['escalation_path']={'owner':'Tender committee','action':'Review cited clauses and original bidder evidence','conflicts':[f['condition'] for f in result['findings'] if f['status']=='conflict']}
 safe_output(result['basis']);return {**s,'result':result,'done':True}
v=StateGraph(dict);v.add_node('independent_verification',verifier_step);v.add_edge(START,'independent_verification');v.add_conditional_edges('independent_verification',lambda s:END if s.get('done') else 'independent_verification');verification_graph=v.compile()
def verify(s):return verification_graph.invoke(s,{'recursion_limit':5})
def initial(run,bid,prompt=PROMPT):return {'run_id':run,'bid':bid,'prompt_version':prompt,'phase':0,'retrieved':{},'started':time.time(),'tool_calls':0,'done':False,'history':[]}
def execute(bid,run='direct',prompt=PROMPT):return verify(research(initial(run,bid,prompt)))['result']
