import fs from 'node:fs/promises'; import path from 'node:path'; import {compile} from 'json-schema-to-typescript'; import {release,readJson} from './common.mjs';
const schema=await readJson(path.join(release,'bundle.schema.json')); const text=await compile(schema,'ContractsCoreBundle',{bannerComment:'/* Generated from contracts-core 0.1.0-dev.2. Runtime validation remains authoritative. */',cwd:release});
await fs.mkdir(path.join(release,'generated'),{recursive:true});await fs.writeFile(path.join(release,'generated/typescript.d.ts'),text);console.log('generated types');
