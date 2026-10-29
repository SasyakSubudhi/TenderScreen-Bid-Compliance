"""Optional offline model-cache import. Run inside a temporary helper container.

Mount an existing Ollama cache at /source read-only and a new managed cache at
/target. Pass the required model identifiers as command-line arguments.
"""
import sys,json,hashlib,shutil
from pathlib import Path
source=Path('/source');target=Path('/target')
for identifier in sys.argv[1:]:
 name,tag=identifier.rsplit(':',1) if ':' in identifier else (identifier,'latest')
 if not all(part and part not in ('.','..') for part in name.split('/')):raise ValueError('invalid model identifier')
 rel=Path('manifests/registry.ollama.ai')/(name if '/' in name else 'library/'+name)/tag
 manifest=json.loads((source/rel).read_text())
 for layer in [manifest['config'],*manifest['layers']]:
  digest=layer['digest'];filename=digest.replace(':','-');origin=source/'blobs'/filename;dest=target/'blobs'/filename;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():
   temp=dest.with_suffix('.tmp');h=hashlib.sha256()
   with origin.open('rb') as incoming,temp.open('wb') as outgoing:
    while chunk:=incoming.read(4*1024*1024):h.update(chunk);outgoing.write(chunk)
   if h.hexdigest()!=digest.split(':',1)[1]:raise ValueError('model blob digest mismatch')
   temp.replace(dest)
 (target/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/rel,target/rel)
 print('Imported and verified model artifact',identifier,flush=True)
