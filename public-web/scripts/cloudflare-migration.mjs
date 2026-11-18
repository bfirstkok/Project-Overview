// Private snapshot -> bounded D1 import SQL. Run from the public-web project.
import {readFileSync,writeFileSync,readdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {MIGRATION_TABLES} from '../server/migration.js';
const [input,output]=process.argv.slice(2);if(!input||!output)throw Error('Usage: node scripts/cloudflare-migration.mjs private-snapshot.json private-import.sql');
const snapshot=JSON.parse(readFileSync(input,'utf8'));
if(snapshot.format!=='askme-migration-v1'||createHash('sha256').update(JSON.stringify(snapshot.tables)).digest('hex')!==snapshot.sha256)throw Error('Snapshot format or checksum mismatch');
const quote=value=>value===null?'NULL':typeof value==='number'&&Number.isFinite(value)?String(value):"'"+String(value).replaceAll("'","''")+"'";
const statements=[];
for(const [table,columns]of Object.entries(MIGRATION_TABLES)){
 if(!Array.isArray(snapshot.tables[table]))throw Error('Missing table '+table);
 for(const row of snapshot.tables[table]){
  if(JSON.stringify(Object.keys(row).sort())!==JSON.stringify([...columns].sort()))throw Error('Schema mismatch '+table);
  const chunks=[];const values=columns.map(key=>{const value=row[key];if(typeof value==='string'&&Buffer.byteLength(value)>16000){chunks.push({key,value});return "''";}return quote(value);});
  statements.push(`INSERT INTO "${table}" (${columns.map(c=>'"'+c+'"').join(',')}) VALUES (${values.join(',')});`);
  for(const {key,value}of chunks){const chars=Array.from(value);for(let at=0;at<chars.length;at+=4000)statements.push(`UPDATE "${table}" SET "${key}"="${key}"||${quote(chars.slice(at,at+4000).join(''))} WHERE "${columns[0]}"=${quote(row[columns[0]])};`);}
 }
}
if(statements.some(sql=>Buffer.byteLength(sql)>90000))throw Error('SQL exceeds D1 statement limit');
const sql=statements.join('\n'),local=new DatabaseSync(':memory:');local.exec('PRAGMA foreign_keys=ON');
for(const file of readdirSync('drizzle').filter(f=>f.endsWith('.sql')).sort())local.exec(readFileSync('drizzle/'+file,'utf8'));local.exec(sql);
for(const [table,columns]of Object.entries(MIGRATION_TABLES)){
 const actual=local.prepare(`SELECT ${columns.map(c=>'"'+c+'"').join(',')} FROM "${table}" ORDER BY "${columns[0]}"`).all();
 if(JSON.stringify(actual)!==JSON.stringify(snapshot.tables[table]))throw Error('Round-trip mismatch '+table);
}
if(local.prepare('PRAGMA foreign_key_check').all().length)throw Error('Foreign key validation failed');
writeFileSync(output,sql,{mode:0o600});console.log(JSON.stringify({checksum:snapshot.sha256,counts:Object.fromEntries(Object.entries(snapshot.tables).map(([k,v])=>[k,v.length])),statements:statements.length,bytes:Buffer.byteLength(sql),verified:true}));
