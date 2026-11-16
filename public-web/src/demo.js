import {blankTask,today} from './core.js';
export function demoTasks(){const day=today(),relative=n=>{const d=new Date(day+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10);};return [
 ['โครงการตัวอย่าง A','สำรวจหน้างาน','In Progress','High',60,['Panithan'],['Jakkarin','khanathippakorn'],2,'รอยืนยันเวลานัดจากลูกค้า'],
 ['โครงการตัวอย่าง B','จัดทำข้อเสนอ','To Do','Normal',0,['Araya','khanathippakorn'],['Sayan'],5,'เตรียมรายการอุปกรณ์และเอกสาร'],
 ['โครงการตัวอย่าง C','ตรวจรายการอุปกรณ์','In Progress','Critical',75,['Sabaipair'],['Jakkarin'],-2,'รอข้อมูลเพิ่มเติมจากทีม'],
 ['โครงการตัวอย่าง A','รวบรวมความต้องการ','Complete','Normal',100,['Panithan'],['Jakkarin'],-5,'ตรวจสอบและส่งเอกสารแล้ว'],
 ['โครงการตัวอย่าง D','นัดนำเสนอ Solution','On Hold','Normal',30,['Araya'],['Sayan'],7,'รอผู้รับผิดชอบยืนยันวัน'],
 ['โครงการตัวอย่าง E','ทดสอบอุปกรณ์','In Progress','High',40,['Sabaipair'],['Jakkarin','Sayan'],0,'ทดสอบตามรายการที่ตกลง'],
 ['โครงการตัวอย่าง B','เตรียม BOM','Complete','Low',100,['Araya'],['Sayan'],-1,'จัดเตรียมรายการเรียบร้อย'],
 ['โครงการตัวอย่าง F','ประสานงาน Vendor','To Do','Normal',0,['Panithan'],['khanathippakorn'],4,'ขอข้อมูลรุ่นและระยะเวลาส่งมอบ']
 ].map((r,i)=>({...blankTask(),id:String(101+i),etag:'demo-1',no:String(i+1),project:r[0],task:r[1],status:r[2],priority:r[3],progress:r[4],sales:r[5],engineer:r[6],start:relative(-7),end:relative(r[7]),notes:r[8]}));}
