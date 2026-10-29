import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.getenv('DATA_DIR', str(ROOT/'data')))
DATA.mkdir(parents=True,exist_ok=True)
MODE=os.getenv('STORE_MODE','sqlite')
REDIS_URL=os.getenv('REDIS_URL','')
PROVIDER_URL=os.getenv('PROVIDER_URL','')
MODEL_ID=os.getenv('MODEL_ID','')
MAX_STEPS=int(os.getenv('MAX_STEPS','12'))
MAX_TOOLS=int(os.getenv('MAX_TOOLS','10'))
RUN_TIMEOUT=float(os.getenv('RUN_TIMEOUT','45'))
CALL_TIMEOUT=float(os.getenv('CALL_TIMEOUT','4'))
SLO_SECONDS=30
PROMPT=os.getenv('PROMPT_VERSION','v2')
