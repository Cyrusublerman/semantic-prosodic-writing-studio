import fs from 'node:fs/promises'; import path from 'node:path'; import {fileURLToPath} from 'node:url';
export const here=path.dirname(fileURLToPath(import.meta.url));
export const release=path.resolve(here,'../schemas/contracts-core/0.1.0-dev.2');
export async function readJson(p){return JSON.parse(await fs.readFile(p,'utf8'));}
export async function writeResult(name,value){await fs.mkdir(path.join(release,'validation'),{recursive:true});await fs.writeFile(path.join(release,'validation',name),JSON.stringify(value,null,2)+'\n');}
