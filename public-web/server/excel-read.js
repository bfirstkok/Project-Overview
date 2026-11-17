const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}});
export const excelClient={clientId:'6f755086-e58e-4533-b1fe-1eddced25ec5',tenantId:'e1c0d622-71bd-42f6-ba07-ab2b2645df6c',scopes:['Files.Read']};
const limit=15*1024*1024;
export async function probeExcel(request,env,fetcher=fetch){
 if(!env.EXCEL_SHARE_URL)return json({error:'ยังไม่ได้ตั้งค่าไฟล์ Excel ต้นฉบับ'},503);
 const authorization=request.headers.get('Authorization')||'';
 if(!/^Bearer [A-Za-z0-9._~-]{20,20000}$/.test(authorization))return json({error:'กรุณาเชื่อม Microsoft ด้วยสิทธิ์ Files.Read'},400);
 try{
  const source=new URL(env.EXCEL_SHARE_URL);if(source.protocol!=='https:'||!source.hostname.endsWith('.sharepoint.com'))return json({error:'การตั้งค่าไฟล์ต้นฉบับไม่ถูกต้อง'},503);
  const share='u!'+btoa(env.EXCEL_SHARE_URL).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  let response=await fetcher('https://graph.microsoft.com/v1.0/shares/'+share+'/driveItem/content',{method:'GET',headers:{Authorization:authorization},redirect:'manual',signal:AbortSignal.timeout(25000)});
  for(let hop=0;hop<4&&[301,302,303,307,308].includes(response.status);hop++){
   const location=response.headers.get('Location');if(!location)return json({error:'Microsoft ไม่ส่งที่อยู่ดาวน์โหลดไฟล์'},502);
   const target=new URL(location);if(target.protocol!=='https:'||!(target.hostname===source.hostname||target.hostname.endsWith('.files.1drv.com')))return json({error:'Microsoft ส่งปลายทางดาวน์โหลดที่ไม่ได้อนุญาต'},502);
   response=await fetcher(target.href,{method:'GET',redirect:'manual',signal:AbortSignal.timeout(25000)});
  }
  if(!response.ok)return json({error:response.status===403?'Microsoft ยังไม่อนุญาตให้อ่านไฟล์นี้ด้วย Files.Read อาจต้องให้เจ้าของไฟล์หรือ IT อนุมัติ':response.status===401?'Microsoft ต้องการให้เข้าสู่ระบบใหม่':'อ่านไฟล์ Excel จาก Microsoft ไม่สำเร็จ',microsoftStatus:response.status},response.status===401||response.status===403?403:502);
  if(Number(response.headers.get('Content-Length'))>limit)return json({error:'ไฟล์ใหญ่เกิน 15 MB'},413);
  const reader=response.body.getReader(),chunks=[];let size=0;
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();return json({error:'ไฟล์ใหญ่เกิน 15 MB'},413);}chunks.push(value);}
  const bytes=new Uint8Array(size);let at=0;for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.length;}
  if(bytes[0]!==80||bytes[1]!==75||bytes[2]!==3||bytes[3]!==4)return json({error:'Microsoft ไม่ได้ส่งไฟล์ .xlsx จึงยังไม่ใช้ข้อมูลนี้'},422);
  const sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
  const result={readable:true,scope:'Files.Read',size,sha256,checkedAt:new Date().toISOString(),syncEnabled:false};
  await env.DB.prepare("INSERT INTO settings(key,value) VALUES('excel_read_check',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").bind(JSON.stringify(result)).run();
  return json(result);
 }catch{return json({error:'ยังติดต่อ Microsoft เพื่ออ่านไฟล์ไม่ได้ กรุณาลองใหม่ ไม่มีการแก้ไฟล์ต้นฉบับ'},502);}
}
