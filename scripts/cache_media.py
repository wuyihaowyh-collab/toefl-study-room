import pathlib,json,urllib.request,urllib.parse,concurrent.futures,subprocess
root=pathlib.Path(__file__).resolve().parent.parent/'site';doc=json.loads((root/'data.json').read_text());refs=set()
def walk(v):
 if isinstance(v,dict):
  for x in v.values():walk(x)
 elif isinstance(v,list):
  for x in v:walk(x)
 elif isinstance(v,str) and v.startswith('https://wofo.cc/toefl/'):refs.add(v)
walk(doc);errors=[];mapping={}
def cache(url):
 target=root/('media'+urllib.parse.urlsplit(url).path)
 try:
  if not target.is_file():
   target.parent.mkdir(parents=True,exist_ok=True)
   for attempt in range(3):
    try:
     data=urllib.request.urlopen(url,timeout=40).read();assert data
     temp=target.with_suffix(target.suffix+'.part');temp.write_bytes(data)
     check=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(temp)],capture_output=True,timeout=20)
     if target.suffix!='.svg':assert check.returncode==0,check.stderr[:200]
     temp.replace(target);break
    except Exception:
     if attempt==2:raise
  mapping[url]=target.relative_to(root).as_posix()
 except Exception as e:errors.append({'url':url,'error':str(e)})
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for i,_ in enumerate(pool.map(cache,sorted(refs)),1):
  if i%200==0:print(i,'/',len(refs),flush=True)
def replace(v):
 if isinstance(v,dict):return {k:replace(x) for k,x in v.items()}
 if isinstance(v,list):return [replace(x) for x in v]
 return mapping.get(v,v) if isinstance(v,str) else v
doc=replace(doc);local=set()
def collect_local(v):
 if isinstance(v,dict):
  for x in v.values():collect_local(x)
 elif isinstance(v,list):
  for x in v:collect_local(x)
 elif isinstance(v,str) and v.startswith('media/'):local.add(v)
collect_local(doc)
doc['meta']['localMedia']=len(local);doc['meta']['onlineMedia']=len(errors)
(root/'data.json').write_text(json.dumps(doc,ensure_ascii=False,separators=(',',':')))
summary=json.loads((root/'catalog-summary.json').read_text());summary['meta']=doc['meta'];(root/'catalog-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(root.parent/'.import-runtime'/'media-report.json').write_text(json.dumps({'checked':len(refs),'errors':errors},ensure_ascii=False,indent=2));print('Done',len(refs),'errors',len(errors),flush=True)
