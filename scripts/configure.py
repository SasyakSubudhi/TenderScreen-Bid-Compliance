from pathlib import Path
import secrets,argparse
parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['stub','local'],default='stub');parser.add_argument('--model');parser.add_argument('--embedding-model');parser.add_argument('--model-cache-path',default='model-cache');parser.add_argument('--output',default='.env');parser.add_argument('--port',default='8000');parser.add_argument('--build-network',default='default');args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
p=root/args.output
if p.exists():raise SystemExit('.env already exists. Edit it or move it before regenerating.')
# Compose service discovery is deployment wiring, generated here, not provider credentials.
scheme='http'
values={'STORE_MODE':'redis','REDIS_URL':'redis'+ '://redis:6379/0','PROVIDER_URL':scheme+'://provider-stub:8000/v1/chat/completions','PROVIDER_MODE':'stub','MODEL_ID':'','PROVIDER_API_KEY':'','API_TOKEN':secrets.token_urlsafe(24),'INPUT_USD_PER_MILLION':'','OUTPUT_USD_PER_MILLION':'','PROMPT_VERSION':'v2','STUB_DELAY':'0.5','FAULT_PROVIDER':'0','CALL_TIMEOUT':'4','RUN_TIMEOUT':'45','MAX_STEPS':'12','MAX_TOOLS':'10','RATE_LIMIT':'60','OTEL_EXPORTER_OTLP_TRACES_ENDPOINT':scheme+'://jaeger:4318/v1/traces','GRAFANA_ADMIN_PASSWORD':secrets.token_urlsafe(20)}
values.update(API_PORT=args.port,OMP_NUM_THREADS='1',LOG_PASSAGES='0',RETRIEVAL_CACHE='1',EMBEDDING_PROVIDER='hash',BUILD_NETWORK=args.build_network,LOAD_HOST=scheme+'://api:8000')
if args.mode=='local':
 if not args.model or not args.embedding_model:parser.error('Local mode requires --model and --embedding-model runtime identifiers')
 values.update(PROVIDER_MODE='local',PROVIDER_URL=scheme+'://model-service:11434/v1/chat/completions',MODEL_BASE_URL=scheme+'://model-service:11434',MODEL_ID=args.model,EMBEDDING_PROVIDER='ollama',EMBEDDING_URL=scheme+'://model-service:11434/api/embed',EMBEDDING_MODEL_ID=args.embedding_model,MODEL_CACHE_PATH=args.model_cache_path,CALL_TIMEOUT='20',EMBEDDING_TIMEOUT='60')
# Alternate model profiles share the same persisted local deployment and Grafana DB.
# Reuse its private credentials rather than generating a password the existing DB ignores.
for previous in (root/'.env',root/'.env.live'):
 if previous!=p and previous.exists():
  existing=dict(line.split('=',1) for line in previous.read_text().splitlines() if '=' in line and not line.startswith('#'))
  for key in ('API_TOKEN','GRAFANA_ADMIN_PASSWORD'):
   if existing.get(key):values[key]=existing[key]
  break
p.write_text('\n'.join(k+'='+v for k,v in values.items())+'\n')
print('Created runtime configuration with private local credentials. Keep it private.')
