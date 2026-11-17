import {PublicClientApplication,InteractionRequiredAuthError} from '@azure/msal-browser';
import {request} from './accounts.js';
import {escapeHTML as e} from './core.js';
let app,config,result,message='',failed=false;
const attemptKey='workboard-excel-read-connecting';
const sharedKey='workboard-excel-shared-read';
const selectedScopes=()=>sessionStorage.getItem(sharedKey)==='1'?config.sharedReadScopes:config.scopes;
export async function initExcelConnection(){
 try{
  config=await request('/api/excel/config');
  if(!config.configured)return false;
  app=new PublicClientApplication({auth:{clientId:config.clientId,authority:'https://login.microsoftonline.com/'+config.tenantId,redirectUri:location.origin+'/',postLogoutRedirectUri:location.origin+'/'},cache:{cacheLocation:'sessionStorage'}});
  await app.initialize();result=await app.handleRedirectPromise();if(result?.account)app.setActiveAccount(result.account);
  const returning=sessionStorage.getItem(attemptKey)==='1';sessionStorage.removeItem(attemptKey);
  if(result||returning){if(result)await checkRead();return true;}
 }catch(error){failed=true;message=friendly(error);sessionStorage.removeItem(attemptKey);return true;}
 return false;
}
function friendly(error){const text=String(error.errorMessage||error.message||'');if(/consent_required|AADSTS65001|AADSTS90094|AADSTS90093|admin.?consent|administrator approval/i.test(text))return 'Microsoft ต้องการการอนุมัติจากผู้ดูแลสำหรับ '+selectedScopes().join(', ')+' ยังไม่ได้เปิดซิงก์อัตโนมัติ';if(/access_denied|user_cancelled/i.test(text))return 'ยังไม่ได้รับอนุญาตให้อ่าน Excel ไม่มีการเปลี่ยนไฟล์ต้นฉบับ';return error.message?.slice(0,350)||'ยังเชื่อม Microsoft ไม่สำเร็จ';}
async function checkRead(){
 const account=result?.account||app.getActiveAccount()||app.getAllAccounts()[0];
 if(!account)throw new Error('กรุณาเชื่อมบัญชี Microsoft ก่อน');
 const email=account.idTokenClaims?.preferred_username||account.username||'';
 if(account.tenantId!==config.tenantId||!email.toLowerCase().endsWith('@askme.co.th'))throw new Error('ใช้บัญชี @askme.co.th เท่านั้น');
 const token=await app.acquireTokenSilent({scopes:selectedScopes(),account});
 const checked=await request('/api/excel/probe','POST',{}, {Authorization:'Bearer '+token.accessToken,'X-Excel-Read-Mode':sessionStorage.getItem(sharedKey)==='1'?'shared':'own'});
 message='อ่านไฟล์ต้นฉบับได้แล้ว ('+new Intl.NumberFormat('th-TH').format(checked.size)+' bytes) · ขั้นตรวจสิทธิ์สำเร็จ ยังไม่เปิดแทนที่ข้อมูลบนเว็บ';failed=false;
}
export function renderExcelConnection(parent){
 const box=document.createElement('section');box.className='chart-card excel-connection';box.innerHTML=`<h2>เชื่อม Excel ต้นฉบับ</h2><p>ทดสอบอ่านไฟล์เดิมผ่าน Microsoft ด้วยสิทธิ์ <strong>Files.Read</strong> เท่านั้น</p><p class="field-note">ขั้นนี้ตรวจสิทธิ์อ่านก่อน ยังไม่เปิดซิงก์อัตโนมัติ และไม่เขียนกลับ Excel</p><button class="button primary" id="excel-read-connect" data-read-mode="own">เชื่อม Microsoft แบบอ่านอย่างเดียว</button><p class="field-note">หากไฟล์อยู่ใน OneDrive ของผู้อื่น อาจต้องใช้ <strong>Files.Read.All</strong> เพื่ออ่านไฟล์ที่บัญชีคุณเข้าถึงได้ ขอบเขตนี้กว้างกว่า Files.Read แต่ไม่มีสิทธิ์เขียน ระบบจะยังอ่านเฉพาะไฟล์ต้นฉบับที่ตั้งไว้</p><button class="button secondary" id="excel-shared-read-connect" data-read-mode="shared">ลองอ่านไฟล์ที่ผู้อื่นแชร์ให้</button><p id="excel-connect-status" role="status" class="${failed?'form-error':'field-note'}">${e(message)}</p>`;
 parent.prepend(box);box.querySelectorAll('[data-read-mode]').forEach(button=>button.onclick=async()=>{const status=box.querySelector('#excel-connect-status');button.disabled=true;try{if(!config?.configured)throw Error('ยังไม่ได้ตั้งค่าไฟล์ต้นฉบับ');if(!app)await initExcelConnection();sessionStorage.setItem(sharedKey,button.dataset.readMode==='shared'?'1':'0');if(app.getActiveAccount()||app.getAllAccounts()[0]){try{await checkRead();status.textContent=message;status.className='field-note';return;}catch(error){if(!(error instanceof InteractionRequiredAuthError))throw error;}}sessionStorage.setItem(attemptKey,'1');await app.loginRedirect({scopes:selectedScopes(),prompt:'select_account'});}catch(error){status.textContent=friendly(error);status.className='form-error';}finally{button.disabled=false;}});
}
