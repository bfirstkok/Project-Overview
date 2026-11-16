import {ROSTER,STATUSES,PRIORITIES} from '../src/core.js';
export const STAFF=[['panithan','Panithan','sales'],['araya','Araya','sales'],['sabaipair','Sabaipair','sales'],['jakkarin','Jakkarin','engineer'],['sayan','Sayan','engineer'],['khanathippakorn','khanathippakorn','intern']];
export const canEdit=(user,task)=>Boolean(user.is_admin||task.creator===user.id||[...(task.sales||[]),...(task.engineer||[])].some(n=>n.toLowerCase()===user.id));
export function validatePayload(body,original){
 if(!body||typeof body!=='object'||Array.isArray(body))return 'ข้อมูลไม่ถูกต้อง';
 const allowed=['project','task','priority','status','start','end','progress','sales','engineer','notes'];
 if(Object.keys(body).some(k=>!allowed.includes(k)))return 'มีช่องข้อมูลที่ไม่อนุญาต';
 for(const k of ['project','task','priority','status','start','end','notes'])if(typeof body[k]!=='string')return 'รูปแบบข้อความไม่ถูกต้อง';
 if(!body.project.trim()||!body.task.trim())return 'กรุณากรอกโครงการและงาน';
 if(body.project.length>500||body.task.length>5000||body.notes.length>10000)return 'ข้อความยาวเกินกำหนด';
 if(!STATUSES.includes(body.status)||!PRIORITIES.includes(body.priority))return 'สถานะหรือ Priority ไม่ถูกต้อง';
 if(!Number.isInteger(body.progress)||body.progress<0||body.progress>100)return 'เปอร์เซ็นต์ต้องเป็นจำนวนเต็มตั้งแต่ 0–100';
 for(const key of ['sales','engineer'])if(!Array.isArray(body[key])||body[key].length>4||body[key].some(n=>typeof n!=='string'||!ROSTER[key].includes(n))||new Set(body[key]).size!==body[key].length)return 'รายชื่อผู้รับผิดชอบไม่ถูกต้อง';
 for(const k of ['start','end'])if(body[k]&&(!/^\d{4}-\d{2}-\d{2}$/.test(body[k])||!Number.isFinite(Date.parse(body[k]))||new Date(body[k]+'T12:00:00Z').toISOString().slice(0,10)!==body[k]))return 'รูปแบบวันที่ไม่ถูกต้อง';
 if(body.start&&body.end&&body.end<body.start&&(!original||body.start!==original.start||body.end!==original.end))return 'วันสิ้นสุดต้องไม่ก่อนวันเริ่มต้น';
 return null;
}
export function passwordError(password){if(typeof password!=='string'||password.length<12||password.length>128)return 'ใช้รหัสผ่าน 12–128 ตัวอักษร';return null;}
export function taskPayload(t){return Object.fromEntries(['project','task','priority','status','start','end','progress','sales','engineer','notes'].map(k=>[k,t[k]]));}
