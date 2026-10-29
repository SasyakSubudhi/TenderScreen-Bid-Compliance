from app.engine import initial,verify
from app.config import ROOT
import json
def test_incomplete_research_is_never_verified():
 bid=json.loads((ROOT/'examples/valid.json').read_text());state=initial('incomplete-regression',bid);state['reason']='loop_or_wall_clock_limit'
 result=verify(state)['result']
 assert result['route']=='seek-clarification'
 assert result['verification']['passed'] is False
 assert result['findings']==[]
