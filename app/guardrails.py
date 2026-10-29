import re
INJECTION=re.compile(r'ignore.{0,35}(instructions|rules|previous)|system\s*prompt|you are now|reveal.{0,20}(secret|key)|<\|.*?\|>|execute.{0,20}(tool|command)|always.{0,15}(approve|qualify|reject)',re.I)
TOXIC=re.compile(r'\b(kill yourself|stupid idiot|hate all|racial slur)\b',re.I)
def inspect(value):
 if isinstance(value,dict):return [e for v in value.values() for e in inspect(v)]
 if isinstance(value,list):return [e for v in value for e in inspect(v)]
 if not isinstance(value,str):return []
 return (['prompt_injection'] if INJECTION.search(value) else [])+(['toxicity'] if TOXIC.search(value) else [])
def safe_output(text):
 if TOXIC.search(text) or re.search(r'\bbid (is|has been) (rejected|qualified|approved)\b',text,re.I):raise ValueError('unauthorized determination or toxic output')
 return text
