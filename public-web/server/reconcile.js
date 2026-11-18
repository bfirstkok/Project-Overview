import {employeeRoster} from './employees.js';
import {referenceRows} from './reference.js';
import {LABELS,ROSTER} from '../src/core.js';
import {taskPayload,validatePayload} from './policy.js';
import {digest,timingEqual} from './security.js';
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const fields=Object.keys(LABELS).filter(k=>k!=='no');
export function mergeTasks(rows,incoming,roster=ROSTER){
 const updates=[],added=[],preserved=[],conflicts=[],unchanged=[],skipped=[];
 const byNo=new Map();for(const row of rows){if(!row.source_data||!row.no)continue;if(byNo.has(row.no))throw Error('เลขงานต้นฉบับซ้ำในเว็บ');byNo.set(row.no,row);}
 for(const t of incoming){const incomingPayload=taskPayload(t),row=byNo.get(String(t.no));
  if(!row){const error=validatePayload(incomingPayload,incomingPayload,roster);if(error){skipped.push({no:t.no,error});continue;}added.push({no:String(t.no),payload:incomingPayload});continue;}
  const current=JSON.parse(row.payload),source=JSON.parse(row.source_data);let baseline=source.baselinePayload;
  if(!baseline){try{baseline=referenceRows([Object.values(LABELS),Object.values(LABELS).map(l=>source.values[l])]).tasks[0];}catch{skipped.push({no:t.no,error:'ไม่พบข้อมูลตั้งต้นสำหรับเทียบ'});continue;}}
  if(!baseline){skipped.push({no:t.no,error:'ไม่พบข้อมูลตั้งต้นสำหรับเทียบ'});continue;}
  const payload={...current},changed=[];
  for(const field of fields){if(equal(current[field],incomingPayload[field]))continue;
   if(equal(current[field],baseline[field])){payload[field]=incomingPayload[field];changed.push(field);}
   else{const detail={no:t.no,field,baseline:baseline[field],web:current[field],excel:incomingPayload[field]};(equal(incomingPayload[field],baseline[field])?preserved:conflicts).push(detail);}
  }
  const error=validatePayload(payload,payload.start===incomingPayload.start&&payload.end===incomingPayload.end?incomingPayload:current,roster);
  if(error){skipped.push({no:t.no,error});continue;}
  const entry={id:row.id,no:row.no,payload,changed,baselinePayload:incomingPayload};
  (changed.length?updates:unchanged).push(entry);
 }
 return {updates,added,preserved,conflicts,unchanged,skipped};
}
export async function reconcilePlan(db){
 const reference=await db.prepare('SELECT id,sha256,filename,tasks FROM excel_references ORDER BY id DESC LIMIT 1').first();if(!reference)throw Error('ยังไม่มีไฟล์อ้างอิง');
 const {results:rows}=await db.prepare('SELECT * FROM tasks ORDER BY id').all();
 const plan=mergeTasks(rows,JSON.parse(reference.tasks),await employeeRoster(db));
 const expected=rows.map(r=>({id:r.id,version:r.version}));
 const token=await digest(JSON.stringify({referenceId:reference.id,hash:reference.sha256,expected,plan}));
 return {...plan,referenceId:reference.id,sha256:reference.sha256,filename:reference.filename,expected,token};
}
export const planSummary=p=>({token:p.token,referenceId:p.referenceId,filename:p.filename,updated:p.updates.length,added:p.added.length,unchanged:p.unchanged.length,preserved:p.preserved,conflicts:p.conflicts,skipped:p.skipped,changes:p.updates.map(t=>({no:t.no,fields:t.changed})),newTasks:p.added.map(t=>({no:t.no,project:t.payload.project,task:t.payload.task}))});
export async function applyReconcile(db,plan,actor,capability=null){
 const id=crypto.randomUUID(),created=Math.floor(Date.now()/1000),summary=planSummary(plan),report=JSON.stringify(summary);
 const b=(sql,...args)=>db.prepare(sql).bind(...args);
 // The first statement captures the backup and checks the entire preview snapshot.
 // A failed CHECK rolls back the whole D1 batch, including assignments and audit.
 const statements=[b(`INSERT INTO reconciliation_runs(id,reference_id,actor,created,report,backup,guard,capability) SELECT ?,?,?,?, ?,json_object('tasks',json((SELECT json_group_array(json_object('id',id,'no',no,'project_id',project_id,'payload',payload,'version',version,'creator',creator,'request_id',request_id,'last_mutation',last_mutation,'source_data',source_data,'created',created,'updated',updated)) FROM tasks)),'assignments',json((SELECT json_group_array(json_object('id',id,'task_id',task_id,'user_id',user_id,'kind',kind)) FROM assignments))), CASE WHEN (SELECT MAX(id) FROM excel_references)=? AND (SELECT count(*) FROM tasks)=json_array_length(?) AND NOT EXISTS(SELECT 1 FROM json_each(?) e LEFT JOIN tasks t ON t.id=json_extract(e.value,'$.id') WHERE t.id IS NULL OR t.version<>json_extract(e.value,'$.version')) THEN 1 ELSE 0 END,?`,id,plan.referenceId,actor,created,report,plan.referenceId,JSON.stringify(plan.expected),JSON.stringify(plan.expected),capability)];
 for(const entry of [...plan.updates,...plan.unchanged,...plan.added]){
  const source=JSON.stringify({referenceId:plan.referenceId,sha256:plan.sha256,baselinePayload:entry.baselinePayload||entry.payload});
  if(entry.id&&!entry.changed.length){statements.push(b('UPDATE tasks SET source_data=?,version=version+1 WHERE id=?',source,entry.id));continue;}
  const payload=JSON.stringify(entry.payload),project=crypto.randomUUID(),requestId=`reference-${plan.referenceId}-${entry.no}`;
  statements.push(b('INSERT OR IGNORE INTO projects(id,title) VALUES(?,?)',project,entry.payload.project.trim()));
  if(entry.id){statements.push(b('UPDATE tasks SET payload=?,project_id=(SELECT id FROM projects WHERE title=?),source_data=?,version=version+1,last_mutation=?,updated=? WHERE id=?',payload,entry.payload.project.trim(),source,id,created,entry.id));}
  else statements.push(b('INSERT INTO tasks(no,project_id,payload,version,creator,request_id,last_mutation,source_data,created,updated) VALUES(?,(SELECT id FROM projects WHERE title=?),?,1,?,?,?,?,?,?)',entry.no,entry.payload.project.trim(),payload,actor,requestId,id,source,created,created));
  const selector=entry.id?'id=?':'request_id=?',key=entry.id||requestId;
  statements.push(b(`DELETE FROM assignments WHERE task_id=(SELECT id FROM tasks WHERE ${selector})`,key));
  for(const kind of ['sales','engineer'])for(const name of entry.payload[kind])statements.push(b(`INSERT INTO assignments(task_id,user_id,kind) SELECT t.id,u.id,? FROM tasks t JOIN users u ON u.name=? WHERE ${entry.id?'t.id=?':selector}`,kind,name,key));
  statements.push(b(`INSERT INTO activities(task_id,actor,before,after,created) SELECT id,?,${entry.id?"json_extract((SELECT e.value FROM reconciliation_runs r,json_each(r.backup,'$.tasks') e WHERE r.id=? AND json_extract(e.value,'$.id')=tasks.id),'$.payload')":'NULL'},?,? FROM tasks WHERE ${selector}`,actor,...(entry.id?[id]:[]),payload,created,key));
 }
 await db.batch(statements);return {...summary,runId:id};
}
export async function reconcileAPI(request,env,user,maintenance=false){
 if(!maintenance&&!user?.is_admin)return json({error:'เฉพาะ Admin'},403);
 const path=new URL(request.url).pathname,db=env.DB;
 const backup=path.match(/^\/api\/reference\/reconcile\/backup\/([a-f0-9-]+)$/);
 if(backup&&request.method==='GET'){const row=await db.prepare('SELECT * FROM reconciliation_runs WHERE id=?').bind(backup[1]).first();return row?json({run:row.id,referenceId:row.reference_id,report:JSON.parse(row.report),backup:JSON.parse(row.backup)}):json({error:'ไม่พบรายการ'},404);}
 if(request.method!=='POST')return json({error:'ไม่พบปลายทาง'},404);
 try{
  if(maintenance&&(!env.RECONCILE_TOKEN||Number(env.RECONCILE_EXPIRES)<Date.now()||!timingEqual(request.headers.get('X-Reconcile-Token')||'',env.RECONCILE_TOKEN)))return json({error:'ไม่อนุญาต'},403);
  const plan=await reconcilePlan(db);
  if(maintenance){if(!env.RECONCILE_TOKEN||Number(env.RECONCILE_EXPIRES)<Date.now()||!timingEqual(request.headers.get('X-Reconcile-Token')||'',env.RECONCILE_TOKEN)||plan.sha256!==env.RECONCILE_SOURCE_HASH)return json({error:'ไม่อนุญาต'},403);if(await db.prepare('SELECT id FROM reconciliation_runs WHERE capability=?').bind(await digest(env.RECONCILE_TOKEN)).first())return json({error:'ดำเนินการแล้ว'},410);}
  if(path.endsWith('/preview'))return json(planSummary(plan));
  if(!path.endsWith('/apply'))return json({error:'ไม่พบปลายทาง'},404);
  const text=await request.text();if(text.length>1000)return json({error:'ข้อมูลใหญ่เกินกำหนด'},413);const input=JSON.parse(text);
  if(input.token!==plan.token)return json({error:'ข้อมูลเปลี่ยนหลัง Preview กรุณาตรวจอีกครั้ง'},409);
  return json(await applyReconcile(db,plan,user.id,maintenance?await digest(env.RECONCILE_TOKEN):null));
 }catch(error){console.error('Reconcile failed',error.message);return json({error:'อัปเดตไม่สำเร็จหรือข้อมูลเปลี่ยน กรุณา Preview อีกครั้ง'},409);}
}
