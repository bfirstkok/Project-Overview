import {rosterFromUsers} from '../src/core.js';
import {randomToken,digest} from './security.js';
export const employeeRoster=async db=>rosterFromUsers((await db.prepare('SELECT id,name,role FROM users ORDER BY name').all()).results);
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
export async function addEmployee(db,request,actor){
 if(!actor.is_admin)return json({error:'เฉพาะ Admin ที่เพิ่มพนักงานได้'},403);
 const text=await request.text();if(text.length>2000)return json({error:'ข้อมูลยาวเกินกำหนด'},413);
 let input;try{input=JSON.parse(text);}catch{return json({error:'ข้อมูลไม่ถูกต้อง'},400);}
 if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(k=>!['name','role'].includes(k)))return json({error:'กรอกเฉพาะชื่อและตำแหน่ง'},400);
 const name=typeof input.name==='string'?input.name.normalize('NFKC').trim().replace(/\s+/g,' '):'';
 if(!name||name.length>80||/[\x00-\x1f\x7f]/.test(name))return json({error:'กรอกชื่อพนักงาน 1–80 ตัวอักษร'},422);
 if(!['sales','engineer','intern'].includes(input.role))return json({error:'เลือกตำแหน่ง Sales, Engineer หรือ Intern'},422);
 const {results:users}=await db.prepare('SELECT id,name FROM users').all();
 if(users.some(u=>u.name.normalize('NFKC').toLowerCase()===name.toLowerCase()))return json({error:'มีพนักงานชื่อนี้แล้ว ใช้ปุ่มสร้างลิงก์ตั้งรหัสผ่านในรายชื่อเดิมได้เลย'},409);
 if(users.length>=200)return json({error:'รองรับพนักงานได้ไม่เกิน 200 คน'},422);
 let id=name.toLowerCase().replace(/[^a-z0-9._-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,40);
 if(id.length<3)id='staff-'+crypto.randomUUID().slice(0,8);
 if(users.some(u=>u.id===id))id=id.slice(0,30)+'-'+crypto.randomUUID().slice(0,8);
 const token=randomToken(),expires=Math.floor(Date.now()/1000)+604800;
 try{await db.batch([db.prepare('INSERT INTO users(id,name,role,is_admin,active) VALUES(?,?,?,0,0)').bind(id,name,input.role),db.prepare('INSERT INTO invites(token_hash,user_id,expires,used) VALUES(?,?,?,0)').bind(await digest(token),id,expires)]);}catch(error){if(/unique/i.test(error.message))return json({error:'ชื่อพนักงานซ้ำ กรุณาโหลดรายชื่อใหม่'},409);throw error;}
 return json({user:{id,name,role:input.role,isAdmin:false,active:false},url:new URL(request.url).origin+'/#invite='+token,expires},201);
}
