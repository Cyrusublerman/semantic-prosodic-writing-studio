#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError
from spws_contracts_core.digests import canonical_json_bytes
from spws_contracts_core.envelope import CoreObjectEnvelope
from spws_contracts_core.release import RELEASE_MODELS, SCHEMA_RELEASE_VERSION
from spws_contracts_core.text_types import TextSpan
ROOT=Path(__file__).resolve().parents[1]; RELEASE=ROOT/'schemas/contracts-core'/SCHEMA_RELEASE_VERSION

def load(p:Path)->Any:return json.loads(p.read_text(encoding='utf-8'))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write-results',action='store_true');args=ap.parse_args()
 failures=[]; schema_def=[]
 for p in sorted((RELEASE/'models').glob('*.schema.json'))+[RELEASE/'schema.json',RELEASE/'bundle.schema.json']:
  try:Draft202012Validator.check_schema(load(p))
  except Exception as e:schema_def.append({'path':str(p.relative_to(RELEASE)),'error':str(e)})
 manifest=load(RELEASE/'fixtures/manifest.json'); results=[]
 for r in manifest['fixtures']:
  inst=load(RELEASE/r['path']); schema=load(RELEASE/'models'/f"{r['model']}.schema.json")
  errors=sorted(e.message for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(inst)); sv=not errors
  pv=True; pe=None
  try:
   obj=RELEASE_MODELS[r['model']].model_validate_json(json.dumps(inst,ensure_ascii=False))
   if isinstance(obj,TextSpan) and r.get('context'): obj.validate_against(r['context']['text'])
   if isinstance(obj,CoreObjectEnvelope) and obj.record_digest is not None and not obj.verify_record_digest(): raise ValueError('record digest verification failed')
  except (ValidationError,ValueError,TypeError) as e:pv=False;pe=str(e)
  if sv!=r['expected_schema_valid']: failures.append(f"{r['id']}: schema {sv}")
  if pv!=r['expected_python_valid']: failures.append(f"{r['id']}: python {pv}")
  if r.get('expected_error_contains') and not pv and r['expected_error_contains'].lower() not in (pe or '').lower(): failures.append(f"{r['id']}: error text")
  results.append({'id':r['id'],'model':r['model'],'schema_valid':sv,'schema_errors':errors,'python_valid':pv,'python_error':pe,'matched_expectation':sv==r['expected_schema_valid'] and pv==r['expected_python_valid']})
 canon=[]
 for c in load(RELEASE/'canonical/cases.json')['cases']:
  raw=canonical_json_bytes(c['input']); ok=raw.hex()==c['canonical_utf8_hex'] and hashlib.sha256(raw).hexdigest()==c['sha256']; canon.append({'id':c['id'],'matched':ok});
  if not ok:failures.append(f"canonical:{c['id']}")
 failures += [f"schema:{x['path']}" for x in schema_def]
 report={'release':SCHEMA_RELEASE_VERSION,'ok':not failures,'schema_count':len(RELEASE_MODELS)+2,'fixture_count':len(results),'schema_definition_errors':schema_def,'fixtures':results,'canonical_cases':canon,'failures':failures}
 if args.write_results:
  (RELEASE/'validation').mkdir(parents=True,exist_ok=True);(RELEASE/'validation/python-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'ok':report['ok'],'fixtures':len(results),'failures':failures}))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
