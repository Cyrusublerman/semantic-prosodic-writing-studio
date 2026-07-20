#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID
from pydantic_core import to_jsonable_python
from spws_contracts_core.digests import digest_json, digest_text
from spws_contracts_core.envelope import CoreObjectEnvelope, ObjectState, PayloadDescriptor, PayloadKind
from spws_contracts_core.extensions import ExtensionRecord
from spws_contracts_core.policy import *
from spws_contracts_core.provenance import *
from spws_contracts_core.quality import *
from spws_contracts_core.references import *
from spws_contracts_core.release import *
from spws_contracts_core.schema import SchemaReference
from spws_contracts_core.text import *
from spws_contracts_core.identifiers import *

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'schemas/contracts-core'/SCHEMA_RELEASE_VERSION
IDS=[
    UUID('019f6fca-9df7-75c0-a30a-1f7469b2a183'),
    UUID('019f6fca-9df7-75c0-a30a-1f831fd36991'),
    UUID('019f6fca-9df7-75c0-a30a-1f99b8101138'),
    UUID('019f6fca-9df7-75c0-a30a-1fab2a5c45b2'),
    UUID('019f6fca-9df7-75c0-a30a-1fb56426902c'),
    UUID('019f6fca-9df7-75c0-a30a-1fcfab9cf9b7'),
    UUID('019f6fca-9df7-75c0-a30a-1fdc9a6c40c7'),
    UUID('019f6fca-9df7-75c0-a30a-1febe9e6781b'),
    UUID('019f6fca-9df7-75c0-a30a-1ff9a69c4995'),
    UUID('019f6fca-9df7-75c0-a30a-2002538f7e08'),
    UUID('019f6fca-9df7-75c0-a30a-201d84d53ef4'),
    UUID('019f6fca-9df7-75c0-a30a-202f6103c282'),
    UUID('019f6fca-9df7-75c0-a30a-2034265fa4a4'),
    UUID('019f6fca-9df7-75c0-a30a-204571fa04c8'),
    UUID('019f6fca-9df7-75c0-a30a-2058a9c84404'),
    UUID('019f6fca-9df7-75c0-a30a-206da18cc9e0'),
    UUID('019f6fca-9df7-75c0-a30a-2075baba426e'),
    UUID('019f6fca-9df7-75c0-a30a-208aa912abfc'),
    UUID('019f6fca-9df7-75c0-a30a-2094b9d40e09'),
    UUID('019f6fca-9df7-75c0-a30a-20a4218bc442'),
    UUID('019f6fca-9df7-75c0-a30a-20bd95b80dde'),
    UUID('019f6fca-9df7-75c0-a30a-20ce40c4c3ab'),
]
NOW=datetime(2026,7,17,0,0,tzinfo=UTC)

def dump(obj): return obj.model_dump(mode='json',by_alias=True,exclude_none=True)
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(to_jsonable_python(data),ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def agent(i=0): return AgentReference(agent_id=IDS[i],agent_type=AgentType.PERSON,display_name='Alexander Einoder')
def activity(a,i=1): return ActivityReference(activity_id=IDS[i],activity_type='spws.activity.ingest',status=ProcessingState.SUCCEEDED,started_at=NOW,ended_at=NOW+timedelta(seconds=1),responsible_agents=(a,))
def policy(): return DirectPolicySummary(privacy=PrivacyPolicy(privacy_class=PrivacyClass.PRIVATE,transmission_class=TransmissionClass.LOCAL_ONLY),retention=RetentionPolicy(retention_class=RetentionClass.PROJECT_LIFETIME,deletion_mode=DeletionMode.TOMBSTONE_ONLY))
def provenance(a,act): return DirectProvenanceSummary(creator=a,creation_activity=act)
def schema_ref(): return SchemaReference(schema_id=schema_id_for('core-object-envelope'),schema_version=SCHEMA_RELEASE_VERSION)
def envelope(text='example', complete=False):
 a=agent(); act=activity(a); obj=IDS[2]; ver=IDS[3]; payload=PayloadDescriptor(payload_kind=PayloadKind.EMBEDDED,media_type='text/plain',value=text,digest=digest_text(text))
 e=CoreObjectEnvelope(schema=schema_ref(),object_type='spws.object.raw_source',object_id=obj,version_id=ver,created_at=NOW,payload=payload,provenance=provenance(a,act),policy=policy())
 return e.with_calculated_record_digest() if complete else e

def _normalise_schema(node):
 if isinstance(node, dict):
  if node.get('format') == 'uuid': node.setdefault('pattern', r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
  for value in node.values(): _normalise_schema(value)
 elif isinstance(node, list):
  for value in node: _normalise_schema(value)

def schema_for(slug, model):
 s=model.model_json_schema(mode='serialization',by_alias=True)
 _normalise_schema(s)
 s['$schema']=SCHEMA_DIALECT; s['$id']=schema_id_for(slug); s['title']=model.__name__; s['x-spws-release']=SCHEMA_RELEASE_VERSION
 return s

def fixture(fid,model,instance,valid=True,tags=(),schema_valid=None,error=None,context=None):
 return {'id':fid,'model':model,'path':f"fixtures/{'valid' if valid else 'invalid'}/{fid}.json",'expected_schema_valid':valid if schema_valid is None else schema_valid,'expected_python_valid':valid,'tags':list(tags),**({'expected_error_contains':error} if error else {}),**({'context':context} if context else {}),'instance':instance}

def build_fixtures():
 a=agent(); act=activity(a); obj=IDS[2]; ver=IDS[3]; other=IDS[4]
 base=dump(envelope()); complete=dump(envelope('complete',True))
 q=lambda p,**kw: dump(QualifiedValue(presence=p,**kw))
 invalid_id={'object_id':'not-a-uuid','object_type':'spws.object.raw_source'}
 invalid_digest={'algorithm':'sha-256','basis':'raw_bytes','value':'bad','byte_length':3,'verified':False}
 parent=dict(base); parent['parent_version_ids']=[parent['version_id']]
 decision=PolicyDecision(decision_id=IDS[5],operation='spws.operation.external_transmission',outcome=PolicyDecisionOutcome.PERMIT,allowed=True,explanation='bad',evaluated_at=NOW)
 bad_policy=dump(policy()); bad_policy['decisions']=[dump(decision)]
 rel=ProvenanceRelation(relation_id=IDS[6],relation_type='spws.prov.derived_from',subject=VersionReference(object_id=obj,version_id=ver),object=VersionReference(object_id=obj,version_id=other))
 bad_rel=dump(rel); bad_rel['object']['version_id']=ver
 text='A😀e\u0301\r\nA repeated A'; owner=VersionReference(object_id=obj,version_id=ver)
 span_emoji=TextSpan(span_id='emoji',representation_id=IDS[7],representation_version=owner,start=1,end=2,quote=TextQuoteSelector(exact='😀'))
 span_comb=TextSpan(span_id='combining',representation_id=IDS[7],representation_version=owner,start=2,end=4,quote=TextQuoteSelector(exact='e\u0301'))
 span_repeat=TextSpan(span_id='repeat',representation_id=IDS[7],representation_version=owner,start=6,end=7,quote=TextQuoteSelector(exact='A',prefix='\r\n',suffix=' repeated'))
 mapping=SpanMapping(mapping_id=IDS[8],source_representation_id=IDS[7],target_representation_id=IDS[9],segments=(SpanMapSegment(raw_start=0,raw_end=5,derived_start=0,derived_end=5,kind=MappingKind.EQUAL),SpanMapSegment(raw_start=5,raw_end=7,derived_start=5,derived_end=6,kind=MappingKind.REPLACE)),source_length=7,target_length=6)
 rights=RightsAssertion(assertion_id=IDS[10],assertion_type='spws.rights.unknown',issuer=a,target=ObjectReference(object_id=obj))
 denied=PolicyDecision(decision_id=IDS[11],operation='spws.operation.external_transmission',outcome=PolicyDecisionOutcome.DENY,allowed=False,explanation='local only',evaluated_at=NOW)
 mix=ContributionRecord(contribution_id=IDS[12],role='spws.contribution.human_combined',agent=a,target=owner,sources=(VersionReference(object_id=IDS[13],version_id=IDS[14]),VersionReference(object_id=IDS[15],version_id=IDS[16])))
 tomb=CoreObjectEnvelope(schema=schema_ref(),object_type='spws.object.tombstone',object_id=obj,version_id=IDS[17],state=ObjectState.TOMBSTONED,created_at=NOW,payload=PayloadDescriptor(payload_kind=PayloadKind.TOMBSTONE),provenance=provenance(a,act),policy=policy())
 failed=FailureRecord(failure_id=IDS[18],code='COC-F-020',name='corrupt_or_missing_payload',scope='payload')
 return [
 fixture('minimal-envelope','core-object-envelope',base,True,('minimal',)),fixture('complete-envelope','core-object-envelope',complete,True,('complete','digest')),
 fixture('qualified-present','qualified-value',q(PresenceState.PRESENT,value='x',evidence_method=EvidenceMethod.HUMAN_ASSERTED),True,('present',)),
 fixture('qualified-ambiguous','qualified-value',q(PresenceState.AMBIGUOUS,alternatives=(AlternativeRecord(value='a'),AlternativeRecord(value='b'))),True,('ambiguous',)),
 fixture('qualified-unavailable','qualified-value',q(PresenceState.UNAVAILABLE),True,('unavailable',)),fixture('qualified-withheld','qualified-value',q(PresenceState.WITHHELD),True,('withheld',)),fixture('qualified-failed','qualified-value',q(PresenceState.FAILED,failures=(failed,)),True,('failed',)),
 fixture('invalid-identity','object-reference',invalid_id,False,('identity',),False,'uuid'),fixture('invalid-digest','digest-record',invalid_digest,False,('digest',),False,'64'),
 fixture('invalid-parent-self-cycle','core-object-envelope',parent,False,('parent-cycle',),True,'own parent'),fixture('invalid-policy-local-only-permit','direct-policy-summary',bad_policy,False,('policy','external-transmission'),True,'forbidden'),fixture('invalid-provenance-self-relation','provenance-relation',bad_rel,False,('provenance',),True,'itself'),
 fixture('unicode-emoji-span','text-span',dump(span_emoji),True,('unicode','emoji'),context={'text':text}),fixture('unicode-combining-span','text-span',dump(span_comb),True,('unicode','combining-mark'),context={'text':text}),fixture('crlf-span-mapping','span-mapping',dump(mapping),True,('crlf',)),fixture('repeated-quote-span','text-span',dump(span_repeat),True,('repeated-quote',),context={'text':text}),
 fixture('unknown-rights-assertion','rights-assertion',dump(rights),True,('rights',)),fixture('external-transmission-denial','policy-decision',dump(denied),True,('external-transmission',)),fixture('mixed-source-contribution','contribution-record',dump(mix),True,('mixed-source',)),fixture('content-free-tombstone','core-object-envelope',dump(tomb),True,('deletion',)),fixture('critical-extension','extension-record',dump(ExtensionRecord(namespace='x.example.test',schema=SchemaReference(schema_id='urn:pkl:spws:schema:contracts-core:extension-record:0.1.0-dev.2',schema_version=SCHEMA_RELEASE_VERSION),critical=True,value={'x':1})),True,('extension',))]

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--clean',action='store_true'); args=ap.parse_args()
 if args.clean and OUT.exists(): shutil.rmtree(OUT)
 (OUT/'models').mkdir(parents=True,exist_ok=True)
 for slug,model in RELEASE_MODELS.items(): write(OUT/'models'/f'{slug}.schema.json',schema_for(slug,model))
 primary=schema_for('core-object-envelope',CoreObjectEnvelope); write(OUT/'schema.json',primary)
 bundle={'$schema':SCHEMA_DIALECT,'$id':BUNDLE_SCHEMA_ID,'title':'Contracts Core Bundle','oneOf':[{'$ref':f'models/{slug}.schema.json'} for slug in RELEASE_MODELS]}; write(OUT/'bundle.schema.json',bundle)
 fixtures=build_fixtures(); manifest=[]
 for f in fixtures:
  write(OUT/f['path'],f.pop('instance')); manifest.append(f)
 write(OUT/'fixtures/manifest.json',{'release':SCHEMA_RELEASE_VERSION,'fixture_count':len(manifest),'fixtures':manifest})
 write(OUT/'examples/minimal-envelope.json',dump(envelope()))
 write(OUT/'examples/complete-envelope.json',dump(envelope('complete',True)))
 write(OUT/'examples/local-only-policy.json',dump(policy()))
 cases=[]
 for cid,value in [('ordered-object',{'b':2,'a':1}),('unicode',{'text':'A😀e\u0301'}),('array',{'x':[3,2,1]}),('nested',{'z':{'b':False,'a':None}})]:
  from spws_contracts_core.digests import canonical_json_bytes
  raw=canonical_json_bytes(value); cases.append({'id':cid,'input':value,'canonical_utf8_hex':raw.hex(),'sha256':hashlib.sha256(raw).hexdigest()})
 write(OUT/'canonical/cases.json',{'cases':cases})
 write(OUT/'release.json',{'package':'contracts-core','version':SCHEMA_RELEASE_VERSION,'status':'prerelease','schema_dialect':SCHEMA_DIALECT,'model_schema_count':len(RELEASE_MODELS),'fixture_count':len(manifest),'bundle_schema_id':BUNDLE_SCHEMA_ID})
 write(OUT/'compatibility.json',{'version':SCHEMA_RELEASE_VERSION,'baseline':True,'backward_compatibility_claimed':False,'supported_major':0,'notes':['First immutable prerelease; proving contracts remain required.']})
 (OUT/'changelog.md').write_text('# contracts-core 0.1.0-dev.2\n\nFirst immutable schema and fixture prerelease.\n',encoding='utf-8')
 print(f'generated {len(RELEASE_MODELS)} model schemas and {len(manifest)} fixtures')
if __name__=='__main__': main()
