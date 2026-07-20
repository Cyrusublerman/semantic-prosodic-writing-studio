import path from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {release,readJson,writeResult} from './common.mjs';
const m=await readJson(path.join(release,'fixtures/manifest.json'));
const ajv=new Ajv2020({strict:true,allErrors:true,validateFormats:true});
addFormats(ajv);
ajv.addKeyword({keyword:'x-spws-release',schemaType:'string',valid:true});
ajv.addKeyword({keyword:'x-spws-timezone',schemaType:'string',valid:true});
const validators=new Map(); const out=[]; const failures=[];
for(const r of m.fixtures){
 let v=validators.get(r.model);
 if(!v){const s=await readJson(path.join(release,'models',`${r.model}.schema.json`));v=ajv.compile(s);validators.set(r.model,v);}
 const i=await readJson(path.join(release,r.path));const valid=Boolean(v(i));
 if(valid!==r.expected_schema_valid)failures.push(r.id);
 out.push({id:r.id,valid,errors:v.errors??[],matched_expectation:valid===r.expected_schema_valid});
}
const report={validator:'ajv',version:'8.20.0',ok:failures.length===0,fixtures:out,failures};
await writeResult('ajv-results.json',report);console.log(JSON.stringify({ok:report.ok,fixtures:out.length,failures}));if(failures.length)process.exit(1);
