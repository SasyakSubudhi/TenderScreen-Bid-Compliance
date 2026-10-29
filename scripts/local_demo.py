import subprocess,time,os,sys
os.environ['STORE_MODE']='sqlite'
import uvicorn
if __name__=='__main__':
 processes=[]
 for role,port in [('research','9101'),('verification','9102')]:
  env={**os.environ,'WORKER_ROLE':role,'WORKER_METRICS_PORT':port}
  processes.append(subprocess.Popen([sys.executable,'-m','app.worker'],env=env))
 try:uvicorn.run('app.api:app',host=os.getenv('BIND_HOST','127.0.0.1'),port=int(os.getenv('PORT','8000')))
 finally:
  for p in processes:p.terminate()
