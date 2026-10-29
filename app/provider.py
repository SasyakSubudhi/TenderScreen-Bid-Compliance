import json,os,time,threading
import httpx
from .config import PROVIDER_URL,MODEL_ID,CALL_TIMEOUT,RUN_TIMEOUT,ROOT
from .store import store
lock=threading.Lock()
ACTION_SCHEMA={'type':'object','properties':{'tool':{'type':'string','enum':['corpus_search','clause_lookup','request_fields','handoff']},'args':{'type':'object','properties':{'query':{'type':'string'},'family':{'type':'string','enum':['tender','policy']},'k':{'type':'integer','minimum':1,'maximum':10},'clause_id':{'type':'string'}}}},'required':['tool','args'],'additionalProperties':False}
class ProviderUnavailable(Exception):pass
def stub_action(state):
 phase=state['phase'];v=state['prompt_version'];bid=state['bid']
 if phase==0:return {'tool':'request_fields','args':{}}
 if phase==1:return {'tool':'corpus_search','args':{'query':'turnover experience earnest money documents local content','family':'tender','k':8}}
 if phase==2 and v=='v2' and bid['category'] in ('startup','mse'):
  return {'tool':'corpus_search','args':{'query':bid['category']+' relaxation prior turnover prior experience quality technical specifications','family':'policy','k':4}}
 if phase==3 and v=='v2':return {'tool':'clause_lookup','args':{'clause_id':'P-STARTUP' if bid['category']=='startup' else 'P-MSE'}}
 return {'tool':'handoff','args':{}}
def call(state):
 key='provider:breaker';breaker=store.get(key,{'failures':0,'open_until':0})
 if breaker['open_until']>time.time():raise ProviderUnavailable('circuit_open')
 prompt=(ROOT/'prompts'/ (state['prompt_version']+'.txt')).read_text()
 failures=[]
 for attempt in range(3):
  remaining=state['started']+RUN_TIMEOUT-time.time()
  if remaining<=0:raise ProviderUnavailable('run_deadline')
  started=time.perf_counter()
  try:
   if PROVIDER_URL:
    headers={'X-Correlation-ID':state['run_id']}
    if os.getenv('PROVIDER_API_KEY'):headers['Authorization']='Bearer '+os.environ['PROVIDER_API_KEY']
    excerpts=[]
    for cid in ('T-TURNOVER','T-EXPERIENCE','P-STARTUP','P-MSE'):
     if cid in state['retrieved']:
      text=state['retrieved'][cid]['text'];offset=max(0,text.find('normally')) if cid=='P-STARTUP' else 0
      excerpts.append({'id':cid,'text':text[offset:offset+(240 if cid.startswith('P-') else 120)]})
    observation={'bid_category':state['bid']['category'],'average_turnover_inr':sum(state['bid']['turnover_inr'])/5,'phase':state['phase'],'tool_history':[x['tool']+':'+str(x['args'].get('clause_id',x['args'].get('family',''))) for x in state.get('history',[])],'retrieved_ids':list(state['retrieved']),'evidence_excerpts':excerpts}
    history=state.get('history',[]);families={c['family'] for c in state['retrieved'].values()}
    if not history:objective='Inspect the bid fields first using request_fields.'
    elif 'tender' not in families:objective='No tender evidence has been retrieved. Retrieve tender conditions using a search for turnover experience EMD documents and local content, k=8.'
    elif state['prompt_version']=='v2' and state['bid']['category'] in ('startup','mse') and 'policy' not in families:objective='Tender evidence is available. Investigate whether policy modifies the turnover or experience criteria for this bidder category. Search policy using relaxation prior turnover prior experience quality technical specifications.'
    elif state['prompt_version']=='v2' and state['bid']['category'] in ('startup','mse') and not any(x['tool']=='clause_lookup' for x in history):objective='Policy evidence is available. Follow up on its cited provision using clause_lookup for P-STARTUP or P-MSE as appropriate to the category.'
    else:objective='Evidence gathering is complete for this limited screen. Handoff to the independent verifier now.'
    catalog='Tool signatures: request_fields args {}; corpus_search args {query: string, family: tender or policy, k: integer 1..10}; clause_lookup args {clause_id: string}; handoff args {}. Return one action only. Never repeat a completed query. Policy IDs: P-STARTUP, P-MSE, G-170. Select a tool for the CURRENT TASK.'
    user_content=json.dumps(state) if os.getenv('PROVIDER_MODE','stub')=='stub' else json.dumps(observation)+'\nCURRENT TASK: '+objective+'\nSelect the tool for CURRENT TASK only, not an earlier task. Return JSON action.'
    payload={'model':MODEL_ID,'messages':[{'role':'system','content':prompt+'\n'+catalog},{'role':'user','content':user_content}],'temperature':0,'max_tokens':120,'response_format':{'type':'json_schema','json_schema':{'name':'research_action','strict':True,'schema':ACTION_SCHEMA}}}
    r=httpx.post(PROVIDER_URL,json=payload,headers=headers,timeout=min(CALL_TIMEOUT,remaining));r.raise_for_status();response=r.json()
    action=json.loads(response['choices'][0]['message']['content']);usage=response.get('usage',{})
    is_stub=os.getenv('PROVIDER_MODE','stub')=='stub'
   else:
    if os.getenv('FAULT_PROVIDER')=='1':raise ProviderUnavailable('injected provider outage')
    time.sleep(float(os.getenv('STUB_DELAY','0')));action=stub_action(state);usage={};is_stub=True
   store.set(key,{'failures':0,'open_until':0})
   pt=usage.get('prompt_tokens');ct=usage.get('completion_tokens')
   pin=os.getenv('INPUT_USD_PER_MILLION');pout=os.getenv('OUTPUT_USD_PER_MILLION')
   local=os.getenv('PROVIDER_MODE')=='local'
   cost=0.0 if is_stub or local else ((pt*float(pin)+ct*float(pout))/1e6 if pt is not None and ct is not None and pin and pout else None)
   store.event(state['run_id'],{'agent':'research','step':'model','prompt_version':state['prompt_version'],'attempt':attempt+1,'latency':time.perf_counter()-started,'prompt_tokens':pt,'completion_tokens':ct,'cost_usd':cost,'usage_kind':'stub_no_tokens' if is_stub else 'provider_reported','provider_mode':os.getenv('PROVIDER_MODE','stub'),'model_identifier':MODEL_ID if not is_stub else None,'action':action})
   return action
  except Exception as e:
   failures.append(type(e).__name__)
   store.event(state['run_id'],{'agent':'research','step':'model_error','attempt':attempt+1,'latency':time.perf_counter()-started,'error':str(e)[:200]})
   if attempt<2:time.sleep(.1*2**attempt)
 store.breaker_failure(key);raise ProviderUnavailable('provider_failed:'+','.join(failures))
