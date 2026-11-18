import test from 'node:test';
import assert from 'node:assert/strict';
import {database} from './d1.mjs';
import {migrationExport,movedResponse} from '../server/migration.js';
import {digest} from '../server/security.js';
import {api} from '../server/api.js';
test('source maintenance mode rejects mutations while preserving sign-in and read access',async()=>{
 const env={DB:database(),MIGRATION_READ_ONLY:'1'};
 const response=await api(new Request('https://source.test/api/tasks',{method:'POST',headers:{Origin:'https://source.test'},body:'{}'}),env);assert.equal(response.status,503);
 assert.equal((await api(new Request('https://source.test/api/session'),env)).status,200);
});
test('migration snapshot preserves account hashes and business data, excludes sessions, and requires expiring credentials',async()=>{
 const DB=database();DB.sql.prepare('INSERT INTO users(id,name,role,password_hash,salt) VALUES(?,?,?,?,?)').run('admin','Admin','intern','salted-test-hash','salt');DB.sql.prepare('INSERT INTO sessions VALUES(?,?,?)').run('session-secret','admin',9999999999);
 const env={DB,MIGRATION_EXPORT_TOKEN:'private-export-token',MIGRATION_EXPORT_EXPIRES:String(Date.now()+60000),MIGRATION_READ_ONLY:'1'};
 const req=token=>new Request('https://source.test/api/maintenance/migration/export',{method:'POST',headers:{'X-Migration-Token':token}});
 assert.equal((await migrationExport(req('wrong'),env)).status,403);const response=await migrationExport(req('private-export-token'),env);assert.equal(response.status,200);const snapshot=await response.json();assert.equal(snapshot.readOnly,true);assert.equal(snapshot.tables.users[0].password_hash,'salted-test-hash');assert.equal(snapshot.tables.sessions,undefined);assert.equal(snapshot.sha256,await digest(JSON.stringify(snapshot.tables)));env.MIGRATION_EXPORT_EXPIRES='1';assert.equal((await migrationExport(req('private-export-token'),env)).status,403);
});
test('old URL redirects only page GETs and never forwards submitted passwords or API requests',()=>{
 const target='https://askme-kkn-workboard.example.workers.dev';assert.equal(movedResponse(new Request('https://old.test/'),target).headers.get('Location'),target+'/');const post=movedResponse(new Request('https://old.test/api/login',{method:'POST',body:'password'}),target);assert.equal(post.status,503);assert.equal(post.headers.get('Location'),null);assert.equal(movedResponse(new Request('https://old.test/'),'https://malicious.example'),null);
});
