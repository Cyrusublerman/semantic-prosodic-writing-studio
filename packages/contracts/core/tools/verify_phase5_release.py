#!/usr/bin/env python3
import hashlib,json,zipfile
from pathlib import Path
from spws_contracts_core.digests import canonical_json_bytes
from spws_contracts_core.release import SCHEMA_RELEASE_VERSION
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'schemas/contracts-core'/SCHEMA_RELEASE_VERSION
m=json.loads((R/'digest.json').read_text());fail=[];records=[]
for x in m['files']:
 p=R/x['path'];raw=p.read_bytes() if p.exists() else b''
 if len(raw)!=x['byte_length'] or hashlib.sha256(raw).hexdigest()!=x['sha256']:fail.append(x['path'])
 records.append({'path':x['path'],'byte_length':x['byte_length'],'sha256':x['sha256']})
if hashlib.sha256(canonical_json_bytes(records)).hexdigest()!=m['release_root_sha256']:fail.append('release_root')
c=json.loads((ROOT/'STAGE5_CAPABILITY_REPORT.json').read_text());a=ROOT/c['distribution_archive']['path'];raw=a.read_bytes()
if hashlib.sha256(raw).hexdigest()!=c['distribution_archive']['sha256']:fail.append('archive_digest')
with zipfile.ZipFile(a) as z:
 if 'digest.json' not in z.namelist() or len(z.namelist())!=m['file_count']+1:fail.append('archive_contents')
 if any(i.date_time!=(1980,1,1,0,0,0) for i in z.infolist()):fail.append('archive_timestamps')
print(json.dumps({'ok':not fail,'files':m['file_count'],'failures':fail}))
if fail:raise SystemExit(1)
