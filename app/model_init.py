"""Populate the model volume using runtime identifiers, then warm inference."""
import os,time,httpx
base=os.environ['MODEL_BASE_URL'].rstrip('/')
for _ in range(60):
 try:
  httpx.get(base+'/api/tags',timeout=3).raise_for_status();break
 except httpx.HTTPError:time.sleep(1)
else:raise RuntimeError('model service unavailable')
available={m['name'] for m in httpx.get(base+'/api/tags').json()['models']}
for identifier in {os.environ['MODEL_ID'],os.environ['EMBEDDING_MODEL_ID']}:
 if identifier not in available:
  r=httpx.post(base+'/api/pull',json={'model':identifier,'stream':False},timeout=1800);r.raise_for_status()
print('Required model artifacts available')
r=httpx.post(base+'/api/generate',json={'model':os.environ['MODEL_ID'],'prompt':'','keep_alive':'30m'},timeout=180);r.raise_for_status()
print('Inference model warmed')
