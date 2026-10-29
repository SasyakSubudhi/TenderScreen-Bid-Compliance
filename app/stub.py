import os,time,json,asyncio
from fastapi import FastAPI,Request,HTTPException
from prometheus_client import generate_latest,CONTENT_TYPE_LATEST,Counter
from fastapi.responses import Response
from .provider import stub_action
app=FastAPI(title='Delayed deterministic model stub')
CALLS=Counter('stub_calls_total','Stub requests')
@app.get('/health')
def health():return {'status':'ok','mode':'stub'}
@app.get('/metrics')
def metrics():return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)
@app.post('/v1/chat/completions')
async def complete(request:Request):
 CALLS.inc()
 if os.getenv('FAULT_PROVIDER')=='1':raise HTTPException(503,'injected outage')
 await asyncio.sleep(float(os.getenv('STUB_DELAY','0.5')))
 payload=await request.json();state=json.loads(payload['messages'][-1]['content']);action=stub_action(state)
 return {'choices':[{'message':{'content':json.dumps(action)}}],'usage':{'prompt_tokens':0,'completion_tokens':0}}
