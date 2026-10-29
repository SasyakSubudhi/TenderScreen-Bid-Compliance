import hashlib,json,math,re,time,os,uuid
from pathlib import Path
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from .config import ROOT,DATA
def tokens(s):return re.findall(r'[a-z0-9]+',s.lower())
class HashEmbedding(Embeddings):
 version='hash512-v1'
 # Deterministic signed hashing. Cheap offline baseline, NOT a semantic transformer.
 def embed_query(self,text):
  v=[0.0]*512
  for t in tokens(text):
   n=int(hashlib.sha256(t.encode()).hexdigest()[:8],16);v[n%512]+=1 if n&512 else -1
  norm=math.sqrt(sum(x*x for x in v)) or 1;return [x/norm for x in v]
 def embed_documents(self,texts):return [self.embed_query(t) for t in texts]
class LocalEmbedding(Embeddings):
 def __init__(self):
  import httpx
  self.url=os.environ['EMBEDDING_URL'];self.model=os.environ['EMBEDDING_MODEL_ID'];self.force=False
  response=httpx.get(self.url.rsplit('/api/',1)[0]+'/api/tags',timeout=10);response.raise_for_status();metadata=next(m for m in response.json()['models'] if m['name']==self.model)
  self.version='ollama:'+self.model+':'+metadata['digest']+':prefixed-v1'
  self.path=DATA/'semantic_cache';self.path.mkdir(exist_ok=True)
 def embed_query(self,text):return self._embed(['search_query: '+text])[0]
 def embed_documents(self,texts):return self._embed(['search_document: '+t for t in texts])
 def _embed(self,texts):
  import httpx
  keys=[hashlib.sha256((self.version+t).encode()).hexdigest() for t in texts];result=[None]*len(texts);missing=[]
  for i,key in enumerate(keys):
   p=self.path/(key+'.json')
   if p.exists() and not self.force:result[i]=json.loads(p.read_text())
   else:missing.append(i)
  if missing:
   response=httpx.post(self.url,json={'model':self.model,'input':[texts[i] for i in missing]},timeout=float(os.getenv('EMBEDDING_TIMEOUT','30')));response.raise_for_status();vectors=response.json()['embeddings']
   if len(vectors)!=len(missing):raise ValueError('embedding result count mismatch')
   for i,vector in zip(missing,vectors):
    norm=math.sqrt(sum(v*v for v in vector)) or 1;result[i]=[v/norm for v in vector]
    tmp=self.path/(keys[i]+'.'+uuid.uuid4().hex+'.tmp');tmp.write_text(json.dumps(result[i]));os.replace(tmp,self.path/(keys[i]+'.json'))
  return result
def embedding_factory():return LocalEmbedding() if os.getenv('EMBEDDING_PROVIDER')=='ollama' else HashEmbedding()
class Corpus:
 def __init__(self):
  self.clauses=json.loads((ROOT/'corpus/clauses.json').read_text(encoding='utf-8'))
  self.by_id={c['id']:c for c in self.clauses};self.embedding=embedding_factory();self.cache={}
  self.index=FAISS.from_documents([Document(page_content=c['text'],metadata={'id':c['id'],'family':c['family']}) for c in self.clauses],self.embedding)
 def search(self,query,family=None,k=4):
  key=(query,family,k)
  if os.getenv('RETRIEVAL_CACHE','1')=='1' and key in self.cache:return self.cache[key]
  docs=self.index.similarity_search(query,k=k,filter={'family':family} if family else None,fetch_k=len(self.clauses))
  result=[self.by_id[d.metadata['id']] for d in docs]
  if os.getenv('RETRIEVAL_CACHE','1')=='1':self.cache[key]=result
  return result
 def lookup(self,clause_id):return self.by_id.get(clause_id)
def ingest(force=False,reembed_ids=None):
 import pypdfium2 as pdfium
 start=time.perf_counter();embedding=embedding_factory();old=json.loads((DATA/'embedding_cache.json').read_text()) if (DATA/'embedding_cache.json').exists() else {};cache={} ;chunks=[];sources=[];recomputed=0
 if isinstance(embedding,LocalEmbedding):embedding.force=force
 manifest=json.loads((ROOT/'corpus/manifest.json').read_text())
 for source in manifest:
  p=ROOT/'corpus'/source['file'];digest=hashlib.sha256(p.read_bytes()).hexdigest();reader=pdfium.PdfDocument(p)
  for page_num,page in enumerate(reader,1):
   text=' '.join(page.get_textpage().get_text_range().split())
   # Page-preserving 1100-character windows, 150-character overlap.
   for offset in range(0,len(text),950):
    text_part=text[offset:offset+1100]
    if not text_part:continue
    key=hashlib.sha256((embedding.version+text_part).encode()).hexdigest()
    refresh=force or key not in old or key in (reembed_ids or [])
    recomputed+=int(refresh)
    if isinstance(embedding,LocalEmbedding):embedding.force=force or key in (reembed_ids or [])
    cache[key]=embedding.embed_documents([text_part])[0] if refresh else old[key]
    chunks.append({'id':key,'source':source['id'],'page':page_num,'text':text_part})
  sources.append({**source,'sha256':digest,'pages':len(reader)})
 if not chunks:raise ValueError('Corpus produced no text chunks')
 if set(reembed_ids or [])-set(cache):raise ValueError('Unknown chunk ID supplied for re-embedding')
 (DATA/'embedding_cache.json').write_text(json.dumps(cache));(DATA/'chunks.json').write_text(json.dumps(chunks))
 changed=[];removed=[];mode='empty'
 if chunks:
  import faiss
  from langchain_community.docstore.in_memory import InMemoryDocstore
  directory=DATA/'full_index';directory.mkdir(exist_ok=True);binary=directory/'index.faiss';metadata=directory/'chunks.json'
  current={c['id']:c for c in chunks};dimensions=len(next(iter(cache.values())))
  if binary.exists() and metadata.exists():
   previous=json.loads(metadata.read_text());raw=faiss.read_index(str(binary))
  else:previous=[];raw=None
  if raw is not None and raw.d==dimensions and raw.ntotal==len(previous):
   docs={c['id']:Document(page_content=c['text'],metadata={k:c[k] for k in ('id','source','page')}) for c in previous}
   index=FAISS(embedding,raw,InMemoryDocstore(docs),{i:c['id'] for i,c in enumerate(previous)})
   old_ids=set(docs);new_ids=set(current);removed=sorted(old_ids-new_ids);changed=sorted((new_ids-old_ids)|(new_ids&set(reembed_ids or []))|(new_ids if force else set()))
   delete=sorted(set(removed)|(set(changed)&old_ids))
   if delete:index.delete(delete)
   if changed:index.add_embeddings([(current[k]['text'],cache[k]) for k in changed],metadatas=[{a:current[k][a] for a in ('id','source','page')} for k in changed],ids=changed)
   mode='incremental_update'
  else:
   changed=list(current);index=FAISS.from_embeddings([(c['text'],cache[c['id']]) for c in chunks],embedding,metadatas=[{'id':c['id'],'source':c['source'],'page':c['page']} for c in chunks],ids=[c['id'] for c in chunks]);mode='initial_build_or_dimension_change'
  faiss.write_index(index.index,str(binary));metadata.write_text(json.dumps([current[index.index_to_docstore_id[i]] for i in range(index.index.ntotal)]))
 result={'built_at':time.time(),'embedding':embedding.version,'chunks':len(chunks),'sources':sources,'seconds':time.perf_counter()-start,'reused_embeddings':len(chunks)-recomputed,'recomputed_embeddings':recomputed}
 result['chunks_per_second']=len(chunks)/max(result['seconds'],.001)
 result.update(index_mode=mode,updated_vectors=len(changed),removed_vectors=len(removed),retained_vectors=len(chunks)-len(changed),targeted_reembedding=sorted(reembed_ids or []))
 (DATA/'index_manifest.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--reembed',action='store_true');parser.add_argument('--reembed-chunk',action='append',default=[]);args=parser.parse_args()
 print(json.dumps(ingest(args.reembed,args.reembed_chunk),indent=2))
