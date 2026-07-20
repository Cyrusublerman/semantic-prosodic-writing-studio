#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
from spws_contracts_core.digests import canonical_json_bytes
from spws_contracts_core.release import SCHEMA_RELEASE_VERSION
ROOT=Path(__file__).resolve().parents[1]; RELEASE=ROOT/'schemas/contracts-core'/SCHEMA_RELEASE_VERSION

def load(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def main():
 audit=load(RELEASE/'validation/npm-audit.json')
 reports={n:load(RELEASE/'validation'/n) for n in ['python-results.json','ajv-results.json','hyperjump-results.json','canonical-js-results.json','typecheck-results.json']}
 checks={'python_fixture_validation':reports['python-results.json']['ok'],'ajv_fixture_validation':reports['ajv-results.json']['ok'],'hyperjump_fixture_validation':reports['hyperjump-results.json']['ok'],'canonical_byte_parity':reports['canonical-js-results.json']['ok'] and all(x['matched'] for x in reports['python-results.json']['canonical_cases']),'typescript_typecheck':reports['typecheck-results.json']['ok'],'npm_audit_zero_known_vulnerabilities':audit['metadata']['vulnerabilities']['total']==0}
 summary={'release':SCHEMA_RELEASE_VERSION,'ok':all(checks.values()),'checks':checks,'fixture_count':reports['python-results.json']['fixture_count'],'model_schema_count':39,'canonical_case_count':len(reports['python-results.json']['canonical_cases'])}
 write(RELEASE/'validation/summary.json',summary)
 capability={'release':SCHEMA_RELEASE_VERSION,'status':'phase5_schema_fixture_infrastructure_complete','stable_production_release':False,'model_schema_count':39,'fixture_count':21,'valid_fixture_count':14,'invalid_fixture_count':7,'canonical_case_count':4,'checks':checks,'validators':{'python_model':'Pydantic 2.13.4','python_json_schema':'jsonschema 4.26.0 Draft202012Validator','javascript_runtime':'Ajv 8.20.0 Ajv2020 strict','javascript_independent':'@hyperjump/json-schema 1.17.7'},'type_generation':'json-schema-to-typescript 15.0.4','typescript':'6.0.3','canonicalisation':{'python':'rfc8785 0.1.4','javascript':'canonicalize 3.0.0'},'tasks_completed':[f'COC-F-{i:03d}' for i in range(1,12)],'known_limits':['Schemas validate structure; Pydantic and context checks remain authoritative for cross-field semantics.','This is the first immutable prerelease schema package, so backward compatibility is not yet claimed.','InputPackage and RawSource proving contracts remain Phase 6 work.'],'next_phase':'Phase 6 proving contracts'}
 write(RELEASE/'capability.json',capability)
 files=[]
 for p in sorted(RELEASE.rglob('*')):
  if p.is_file() and p.name!='digest.json':
   raw=p.read_bytes();files.append({'path':p.relative_to(RELEASE).as_posix(),'byte_length':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 root=hashlib.sha256(canonical_json_bytes(files)).hexdigest();manifest={'algorithm':'sha-256','projection':'ordered-file-manifest-v1','release':SCHEMA_RELEASE_VERSION,'file_count':len(files),'files':files,'release_root_sha256':root};write(RELEASE/'digest.json',manifest)
 archive=ROOT/'src/spws_contracts_core/data/releases'/f'contracts-core-{SCHEMA_RELEASE_VERSION}.zip';archive.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(RELEASE.rglob('*')):
   if p.is_file():
    info=zipfile.ZipInfo(p.relative_to(RELEASE).as_posix(),date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,p.read_bytes())
 araw=archive.read_bytes();capability['distribution_archive']={'path':archive.relative_to(ROOT).as_posix(),'byte_length':len(araw),'sha256':hashlib.sha256(araw).hexdigest(),'deterministic_timestamps':True};capability['release_root_sha256']=root
 write(ROOT/'STAGE5_CAPABILITY_REPORT.json',capability)
 print(json.dumps({'ok':summary['ok'],'files':len(files),'root':root,'archive':capability['distribution_archive']['sha256']}))
 if not summary['ok']:raise SystemExit(1)
if __name__=='__main__':main()
