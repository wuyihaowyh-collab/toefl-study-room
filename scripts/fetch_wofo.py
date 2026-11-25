import json,urllib.request,concurrent.futures,datetime,pathlib
out=pathlib.Path(__file__).resolve().parent.parent/'.import-runtime'/'source';out.mkdir(parents=True,exist_ok=True);errors=[]
def get(i):
 p=out/f'mock-{i}.json'
 if p.exists():return json.loads(p.read_text())
 for attempt in range(3):
  try:
   with urllib.request.urlopen(f'https://wofo.cc/api/toefl/tests/mock-{i}/definition',timeout=30) as r:d=json.load(r)
   assert d.get('ok') and d.get('definition',{}).get('questions')
   p.write_text(json.dumps(d,ensure_ascii=False));return d
  except Exception as e:
   if attempt==2:errors.append({'id':i,'error':str(e)})
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(get,range(1,71)))
raw={'retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':[{'testId':f'mock-{i}','definition':json.loads((out/f'mock-{i}.json').read_text())['definition']} for i in range(1,71) if (out/f'mock-{i}.json').exists()],'errors':errors}
(out/'raw.json').write_text(json.dumps(raw,ensure_ascii=False));print('Fetched',len(raw['tests']),'errors',errors)
