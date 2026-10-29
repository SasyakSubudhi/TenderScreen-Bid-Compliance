import json
import numpy as np
import faiss
from app import corpus
def test_targeted_reembedding_preserves_other_vectors(tmp_path,monkeypatch):
 monkeypatch.setattr(corpus,'DATA',tmp_path);monkeypatch.setenv('EMBEDDING_PROVIDER','hash')
 first=corpus.ingest();assert first['chunks']>0
 directory=tmp_path/'full_index';before=faiss.read_index(str(directory/'index.faiss'));old=json.loads((directory/'chunks.json').read_text());vectors={c['id']:before.reconstruct(i) for i,c in enumerate(old)}
 again=corpus.ingest();assert again['updated_vectors']==0;assert again['reused_embeddings']==first['chunks']
 target=old[len(old)//2]['id'];updated=corpus.ingest(reembed_ids=[target]);assert updated['updated_vectors']==1;assert updated['recomputed_embeddings']==1;assert updated['retained_vectors']==first['chunks']-1
 after=faiss.read_index(str(directory/'index.faiss'));new=json.loads((directory/'chunks.json').read_text());assert after.ntotal==before.ntotal
 for i,c in enumerate(new):
  if c['id']!=target:assert np.array_equal(vectors[c['id']],after.reconstruct(i))
