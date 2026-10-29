"""Exercise real asynchronous HTTP runs and validate cited outcomes."""
import argparse,json,os,time,uuid
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
def check(base,token):
 results=[]
 with httpx.Client(base_url=base,headers={'Authorization':'Bearer '+token},timeout=10) as client:
  for example,expected in [('valid','pass-to-technical-evaluation'),('startup_conflict','seek-clarification')]:
   body=json.loads((ROOT/'examples'/f'{example}.json').read_text());body['bidder_name']='Smoke '+uuid.uuid4().hex[:8]
   started=time.perf_counter();r=client.post('/v1/runs',json=body);r.raise_for_status();run=r.json()['run_id']
   while time.perf_counter()-started<90:
    response=client.get('/v1/runs/'+run);response.raise_for_status();record=response.json()
    if record['status']=='completed':break
    time.sleep(.2)
   else:raise TimeoutError(run)
   result=record['result'];assert result['route']==expected,result;assert result['verification']['passed'],result
   trace=client.get('/v1/runs/'+run+'/trace').json();agents={e.get('agent') for e in trace['events']};assert {'research','verification'}<=agents
   assert len({(e.get('service_instance','local'),e['process_id']) for e in trace['events']})>=2
   if example=='startup_conflict':assert {'T-TURNOVER','P-STARTUP'}<={c['id'] for c in result['citations']}
   results.append({'example':example,'run':record,'trace':trace,'observed_seconds':time.perf_counter()-started})
  before=client.get('/v1/dashboard').json()['runs'];bad=client.post('/v1/runs',json={**body,'eligible_orders':-1});assert bad.status_code==422 and not bad.json()['agent_started'];assert client.get('/v1/dashboard').json()['runs']==before
 return {'runs':results,'quarantine_no_run':'passed'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base-url',required=True);p.add_argument('--output',default='smoke.json');args=p.parse_args()
 result=check(args.base_url,os.getenv('API_TOKEN',''));out=ROOT/'evidence'/args.output;out.write_text(json.dumps(result,indent=2));print(json.dumps({'examples':len(result['runs']),'quarantine_no_run':result['quarantine_no_run']}))
