import path from 'node:path';
import {registerSchema,validate} from '@hyperjump/json-schema/draft-2020-12';
import {release,readJson,writeResult} from './common.mjs';
const m=await readJson(path.join(release,'fixtures/manifest.json'));const registered=new Set();const out=[];const failures=[];
for(const r of m.fixtures){
 const s=await readJson(path.join(release,'models',`${r.model}.schema.json`));
 if(!registered.has(r.model)){registerSchema(s,s.$id);registered.add(r.model);}
 const i=await readJson(path.join(release,r.path));const result=await validate(s.$id,i);const valid=result.valid;
 if(valid!==r.expected_schema_valid)failures.push(r.id);out.push({id:r.id,valid,matched_expectation:valid===r.expected_schema_valid});
}
const report={validator:'hyperjump',version:'1.17.7',ok:failures.length===0,fixtures:out,failures};await writeResult('hyperjump-results.json',report);console.log(JSON.stringify({ok:report.ok,fixtures:out.length,failures}));if(failures.length)process.exit(1);
