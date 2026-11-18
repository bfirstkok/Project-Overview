import {timingEqual,digest} from './security.js';
export const MIGRATION_TABLES={
 users:['id','name','role','is_admin','password_hash','salt','active'],
 projects:['id','title'],
 tasks:['id','no','project_id','payload','version','creator','request_id','last_mutation','source_data','created','updated'],
 assignments:['id','task_id','user_id','kind'],
 activities:['id','task_id','actor','before','after','created'],
 settings:['key','value'],
 excel_references:['id','filename','sha256','size','imported_at','imported_by','source_modified','row_count','tasks','file_base64'],
 reconciliation_runs:['id','reference_id','actor','created','report','backup','guard','capability']
};
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
export async function migrationExport(request,env){
 if(request.method!=='POST')return json({error:'Method not allowed'},405);
 if(!env.MIGRATION_EXPORT_TOKEN||!Number.isFinite(Number(env.MIGRATION_EXPORT_EXPIRES))||Number(env.MIGRATION_EXPORT_EXPIRES)<Date.now()||!timingEqual(request.headers.get('X-Migration-Token')||'',env.MIGRATION_EXPORT_TOKEN))return json({error:'ไม่อนุญาต'},403);
 // One SQL statement gives all business tables the same consistent snapshot.
 // Existing sessions, invitation tokens and login telemetry are deliberately excluded.
 const fields=Object.entries(MIGRATION_TABLES).map(([table,columns])=>`'${table}',json((SELECT json_group_array(json_object(${columns.map(c=>`'${c}',"${c}"`).join(',')})) FROM (SELECT * FROM "${table}" ORDER BY "${columns[0]}")))`).join(',');
 const snapshot=await env.DB.prepare(`SELECT json_object(${fields}) AS snapshot`).first();
 const sha256=await digest(snapshot.snapshot),tables=JSON.parse(snapshot.snapshot);
 return json({format:'askme-migration-v1',createdAt:new Date().toISOString(),readOnly:env.MIGRATION_READ_ONLY==='1',sha256,tables});
}
export function movedResponse(request,origin){
 if(!/^https:\/\/[a-z0-9-]+\.[a-z0-9-]+\.workers\.dev$/.test(origin||''))return null;
 const url=new URL(request.url);
 if(!url.pathname.startsWith('/api/')&&['GET','HEAD'].includes(request.method))return new Response(null,{status:302,headers:{Location:origin+url.pathname,'Cache-Control':'no-store'}});
 return json({error:'ระบบย้ายแล้ว กรุณาเปิด '+origin,url:origin},503);
}
