import {readSheet} from 'read-excel-file/universal';
import {unzipSync,strFromU8} from 'fflate';
import {LABELS,STATUSES,PRIORITIES,people,ROSTER} from '../src/core.js';
const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}});
const normal=value=>String(value??'').replace(/[\s.%_]/g,'').toLowerCase();
const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
function checkZip(bytes){
 if(bytes.length>500000||bytes.length<22)throw Error('ใช้ไฟล์ .xlsx ขนาดไม่เกิน 500 KB');
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);let end=-1;
 for(let i=bytes.length-22;i>=Math.max(0,bytes.length-65557);i--)if(view.getUint32(i,true)===0x06054b50){end=i;break;}
 if(end<0)throw Error('ไฟล์ .xlsx ไม่สมบูรณ์');const count=view.getUint16(end+10,true);let at=view.getUint32(end+16,true),total=0;
 if(count>2000)throw Error('ไฟล์มีส่วนประกอบมากเกินกำหนด');
 for(let i=0;i<count;i++){if(at+46>bytes.length||view.getUint32(at,true)!==0x02014b50)throw Error('โครงสร้างไฟล์ไม่ถูกต้อง');total+=view.getUint32(at+24,true);if(total>20*1024*1024)throw Error('ข้อมูลเมื่อแตกไฟล์ใหญ่เกินกำหนด');at+=46+view.getUint16(at+28,true)+view.getUint16(at+30,true)+view.getUint16(at+32,true);}
}
export function sourceDate(value){
 if(value===null||value===undefined||value==='')return '';
 let date;if(value instanceof Date)date=value.toISOString().slice(0,10);else if(typeof value==='number')date=new Date(Date.UTC(1899,11,30)+Math.round(value)*86400000).toISOString().slice(0,10);else{const text=String(value).trim();let match=text.match(/^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/);if(match){let year=Number(match[1]);if(year>2400)year-=543;date=`${year}-${match[2]}-${match[3]}`;}else{match=text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2}|\d{4})$/);if(!match)throw Error('รูปแบบวันที่ไม่ถูกต้อง');let year=Number(match[3]);if(year<100)year+=2000;if(year>2400)year-=543;date=`${year}-${match[2].padStart(2,'0')}-${match[1].padStart(2,'0')}`;}}
 if(Number(date.slice(0,4))>2400)date=String(Number(date.slice(0,4))-543)+date.slice(4);
 if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(Date.parse(date))||new Date(date+'T12:00:00Z').toISOString().slice(0,10)!==date)throw Error('วันที่ไม่มีอยู่จริง');return date;
}
export function referenceRows(rows){
 const header=rows.slice(0,20).findIndex(row=>row&&Object.values(LABELS).every(label=>row.some(cell=>normal(cell)===normal(label))));if(header<0)throw Error('ไม่พบหัวตาราง 11 คอลัมน์ตามไฟล์ To-do List');
 const columns=Object.fromEntries(Object.entries(LABELS).map(([key,label])=>[key,rows[header].findIndex(cell=>normal(cell)===normal(label))]));
 const tasks=[],errors=[],warnings=[],ids=new Set();let skipped=0;
 for(let i=header+1;i<rows.length;i++){const row=rows[i]||[],value=key=>row[columns[key]],project=String(value('project')??''),task=String(value('task')??'');if(!project.trim()&&!task.trim()){skipped++;continue;}
  try{const no=Number(value('no'));if(!Number.isInteger(no)||no<1)throw Error('No. ไม่ถูกต้อง');if(ids.has(no))throw Error('No. ซ้ำ');ids.add(no);
   const raw=value('progress');if(raw===null||raw===undefined||raw==='')throw Error('ไม่พบ % Complete');let progress=typeof raw==='string'&&raw.trim().endsWith('%')?Number(raw.trim().slice(0,-1)):Number(raw);if(!(typeof raw==='string'&&raw.trim().endsWith('%'))&&progress<=1)progress*=100;if(!Number.isFinite(progress)||progress<0||progress>100)throw Error('% Complete ต้องอยู่ระหว่าง 0–100');progress=Math.round(progress);
   const start=sourceDate(value('start')),end=sourceDate(value('end'));
   const canonical=(choices,v)=>choices.find(c=>c.toLowerCase()===String(v??'').trim().toLowerCase())||String(v??'');
   const names=kind=>people(value(kind),kind).map(n=>ROSTER[kind].find(p=>p.toLowerCase()===n.toLowerCase())||n);
   const t={id:String(no),no:String(no),project,task,priority:canonical(PRIORITIES,value('priority')),status:canonical(STATUSES,value('status')),start,end,progress,sales:names('sales'),engineer:names('engineer'),notes:String(value('notes')??''),canEdit:false,source:'reference'};
   if(project.length>5000||task.length>10000||t.notes.length>20000)throw Error('ข้อความยาวเกินกำหนด');
   if(start&&end&&end<start)warnings.push({row:i+1,no,message:'คงวันที่สิ้นสุดก่อนวันเริ่มต้นตามไฟล์เดิม'});
   for(const kind of ['sales','engineer'])for(const name of t[kind])if(!ROSTER[kind].includes(name))warnings.push({row:i+1,no,message:'คงชื่อจากไฟล์: '+name});tasks.push(t);
  }catch(error){errors.push({row:i+1,message:error.message});}
 }
 if(tasks.length>5000)throw Error('รองรับไม่เกิน 5,000 งานต่อไฟล์');if(!tasks.length&&!errors.length)throw Error('ไม่พบงานในไฟล์');return {tasks,errors,warnings,skipped};
}
export async function parseReference(bytes,filename){
 checkZip(bytes);if(typeof filename!=='string'||filename.length>250||/[\r\n]/.test(filename)||!filename.toLowerCase().endsWith('.xlsx'))throw Error('เลือกไฟล์ .xlsx');
 const rows=await readSheet(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),{sheet:'To-Do List',trim:false});const result=referenceRows(rows);
 if(new TextEncoder().encode(JSON.stringify(result.tasks)).length+Math.ceil(bytes.length/3)*4>1900000)throw Error('ข้อมูลอ้างอิงใหญ่เกินกำหนด');
 const metadata=unzipSync(bytes,{filter:file=>file.name==='docProps/core.xml'});const xml=metadata['docProps/core.xml']?strFromU8(metadata['docProps/core.xml']):'';const modified=xml.match(/<dcterms:modified[^>]*>([^<]+)</)?.[1];
 return {...result,filename,size:bytes.length,sha256:await hash(bytes),sourceModified:modified&&Number.isFinite(Date.parse(modified))?new Date(modified).toISOString():null};
}
const info=row=>({id:row.id,filename:row.filename,sha256:row.sha256,size:row.size,rowCount:row.row_count,importedAt:row.imported_at,importedBy:row.imported_by,sourceModified:row.source_modified});
export async function referenceAPI(request,env,user){
 const path=new URL(request.url).pathname,db=env.DB;
 if(path==='/api/reference'&&request.method==='GET'){const row=await db.prepare('SELECT * FROM excel_references ORDER BY id DESC LIMIT 1').first();return json(row?{reference:info(row),tasks:JSON.parse(row.tasks)}:{reference:null,tasks:[]});}
 const file=path.match(/^\/api\/reference\/file\/(\d+)$/);if(file&&request.method==='GET'){const row=await db.prepare('SELECT * FROM excel_references WHERE id=?').bind(Number(file[1])).first();if(!row)return json({error:'ไม่พบสำเนาไฟล์'},404);const binary=atob(row.file_base64),bytes=Uint8Array.from(binary,c=>c.charCodeAt(0));return new Response(bytes,{headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','Content-Disposition':"attachment; filename=AskMe-reference.xlsx; filename*=UTF-8''"+encodeURIComponent(row.filename),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});}
 if(!user.is_admin)return json({error:'เฉพาะ Admin ที่บันทึกสำเนาอ้างอิงใหม่ได้'},403);
 if(!['/api/reference/preview','/api/reference/import'].includes(path)||request.method!=='POST')return json({error:'ไม่พบปลายทาง'},404);
 try{
  if(Number(request.headers.get('Content-Length'))>700000)return json({error:'ไฟล์ใหญ่เกินกำหนด'},413);
  const reader=request.body?.getReader();if(!reader)throw Error('เลือกไฟล์ Excel');const chunks=[];let size=0;while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>700000){await reader.cancel();return json({error:'ไฟล์ใหญ่เกินกำหนด'},413);}chunks.push(value);}const body=new Uint8Array(size);let at=0;for(const chunk of chunks){body.set(chunk,at);at+=chunk.length;}
  const form=await new Request(request.url,{method:'POST',headers:request.headers,body}).formData(),file=form.get('file');if(!file||typeof file.arrayBuffer!=='function')throw Error('เลือกไฟล์ Excel');const bytes=new Uint8Array(await file.arrayBuffer()),parsed=await parseReference(bytes,file.name);
  const current=(await db.prepare('SELECT max(id) AS id FROM excel_references').first()).id||0;
  if(path.endsWith('/preview'))return json({...parsed,tasks:parsed.tasks.slice(0,5),rowCount:parsed.tasks.length,currentId:current});
  if(parsed.errors.length)return json({error:'มีข้อมูลที่อ่านไม่ได้ กรุณาตรวจ Preview',errors:parsed.errors},422);
  if(form.get('expectedHash')!==parsed.sha256)return json({error:'ไฟล์เปลี่ยนหลัง Preview กรุณาตรวจอีกครั้ง'},409);
  const existing=await db.prepare('SELECT * FROM excel_references WHERE sha256=?').bind(parsed.sha256).first();if(existing)return json({reference:info(existing),duplicate:true});
  const expected=Number(form.get('expectedCurrentId'));if(!Number.isInteger(expected)||expected<0)throw Error('กรุณาตรวจ Preview ก่อน');
  let binary='';for(let offset=0;offset<bytes.length;offset+=8192)binary+=String.fromCharCode(...bytes.subarray(offset,offset+8192));
  const inserted=await db.prepare('INSERT OR IGNORE INTO excel_references(filename,sha256,size,imported_at,imported_by,source_modified,row_count,tasks,file_base64) SELECT ?,?,?,?,?,?,?,?,? WHERE (SELECT COALESCE(MAX(id),0) FROM excel_references)=?').bind(parsed.filename,parsed.sha256,parsed.size,Math.floor(Date.now()/1000),user.id,parsed.sourceModified,parsed.tasks.length,JSON.stringify(parsed.tasks),btoa(binary),expected).run();
  if(inserted.meta.changes!==1){const duplicate=await db.prepare('SELECT * FROM excel_references WHERE sha256=?').bind(parsed.sha256).first();if(duplicate)return json({reference:info(duplicate),duplicate:true});return json({error:'มีสำเนาใหม่ถูกบันทึกแล้ว กรุณา Preview อีกครั้ง'},409);}
  const row=await db.prepare('SELECT * FROM excel_references WHERE sha256=?').bind(parsed.sha256).first();return json({reference:info(row),warnings:parsed.warnings},201);
 }catch(error){return json({error:error.message?.slice(0,250)||'อ่านไฟล์ไม่สำเร็จ'},422);}
}
