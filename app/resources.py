"""Internal, read-only Docker statistics exporter, scoped to this Compose project."""
import os,time,json
import httpx,redis
from prometheus_client import Gauge,start_http_server
CPU=Gauge('container_cpu_usage_seconds_total','Cumulative container CPU seconds',['name'])
MEM=Gauge('container_memory_working_set_bytes','Working set memory',['name'])
UP=Gauge('container_running','Container running state',['name'])
REDIS_UP=Gauge('redis_up','Redis reachability')
REDIS_MEM=Gauge('redis_memory_used_bytes','Redis used memory')
REDIS_CLIENTS=Gauge('redis_connected_clients','Redis connected clients')
def main():
 start_http_server(9100)
 client=httpx.Client(transport=httpx.HTTPTransport(uds='/var/run/docker.sock'),base_url='http://docker',timeout=3)
 queue=redis.Redis.from_url(os.environ['REDIS_URL'],socket_timeout=3)
 project=os.environ['PROJECT_NAME']
 while True:
  try:
   response=client.get('/containers/json',params={'all':'true','filters':json.dumps({'label':['com.docker.compose.project='+project]})});response.raise_for_status()
   for container in response.json():
    name=container['Names'][0].lstrip('/');running=container['State']=='running';UP.labels(name).set(running)
    if not running:continue
    stats=client.get('/containers/'+container['Id']+'/stats',params={'stream':'false','one-shot':'true'});stats.raise_for_status();s=stats.json()
    CPU.labels(name).set(s.get('cpu_stats',{}).get('cpu_usage',{}).get('total_usage',0)/1e9)
    m=s.get('memory_stats',{});MEM.labels(name).set(max(0,m.get('usage',0)-m.get('stats',{}).get('inactive_file',0)))
   info=queue.info();REDIS_UP.set(1);REDIS_MEM.set(info.get('used_memory',0));REDIS_CLIENTS.set(info.get('connected_clients',0))
  except Exception as e:
   REDIS_UP.set(0);print(json.dumps({'service':'resource-exporter','error':type(e).__name__}),flush=True)
  time.sleep(5)
if __name__=='__main__':main()
