import {PublicClientApplication,InteractionRequiredAuthError} from '@azure/msal-browser';
import {mapColumns,toTask,toFields,validateTask} from './core.js';
export class GraphError extends Error {constructor(message,status){super(message);this.status=status;}}
export class ListsStore {
  constructor(config,auth,fetcher=fetch){this.config=config;this.auth=auth;this.fetcher=fetcher;}
  async request(path,options={}){
    const url=new URL(path,'https://graph.microsoft.com/v1.0/');
    if(url.origin!=='https://graph.microsoft.com'||!url.pathname.startsWith('/v1.0/'))throw Error('ปลายทางข้อมูลไม่ถูกต้อง');
    const token=await this.auth.token();
    const response=await this.fetcher(url,{...options,headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json',...options.headers}});
    if(!response.ok){let detail;try{detail=await response.json();}catch{}const message=response.status===412?'มีเพื่อนแก้ไขงานนี้แล้ว กรุณาโหลดข้อมูลล่าสุดแล้วตรวจการเปลี่ยนแปลงก่อนบันทึก':response.status===403?'บัญชีนี้ยังไม่มีสิทธิ์เข้าถึง Lists หรือยังไม่ได้รับอนุมัติการเชื่อมต่อจาก IT':response.status===429?'Microsoft กำลังจำกัดจำนวนคำขอ กรุณารอสักครู่แล้วลองใหม่':response.status===401?'เซสชันหมดอายุ กรุณาเข้าสู่ระบบ Microsoft อีกครั้ง':`บันทึกหรืออ่านข้อมูลไม่สำเร็จ (${response.status}) ${detail?.error?.message||''}`;throw new GraphError(message,response.status);}
    return response.status===204?null:response.json();
  }
  async collection(path){const records=[];let next=path;while(next){const data=await this.request(next);records.push(...data.value);next=data['@odata.nextLink'];}return records;}
  async connect(){const c=this.config;const site=await this.request(`sites/${encodeURIComponent(c.siteHostname)}:${c.sitePath}`);this.base=`sites/${encodeURIComponent(site.id)}/lists/${encodeURIComponent(c.listId)}`;this.columns=mapColumns(await this.collection(`${this.base}/columns`));for(const k of ['sales','engineer'])if(!this.columns[k].choice?.allowMultipleSelections)throw Error(`ตั้งคอลัมน์ ${k} ใน Lists ให้เลือกได้หลายคนก่อน`);return this.load();}
  async load(){return (await this.collection(`${this.base}/items?$expand=fields&$top=200`)).map(item=>toTask(item,this.columns)).filter(t=>t.project.trim()||t.task.trim());}
  async update(task,original){const errors=validateTask(task,original);if(errors.length)throw Error(errors.join(' · '));if(!original.etag)throw Error('ไม่พบรุ่นข้อมูล กรุณาโหลดรายการใหม่ก่อนแก้ไข');const fields=toFields(task,this.columns,original);if(!Object.keys(fields).length)return original;await this.request(`${this.base}/items/${encodeURIComponent(task.id)}/fields`,{method:'PATCH',headers:{'If-Match':original.etag},body:JSON.stringify(fields)});return toTask(await this.request(`${this.base}/items/${encodeURIComponent(task.id)}?$expand=fields`),this.columns);}
  async create(task){const errors=validateTask(task);if(errors.length)throw Error(errors.join(' · '));const nonce=`WB-${crypto.randomUUID()}`;const payload={...task,no:nonce};let item;try{item=await this.request(`${this.base}/items`,{method:'POST',body:JSON.stringify({fields:toFields(payload,this.columns)})});}catch(error){if(error.status)throw error;throw Error('ยังยืนยันผลการเพิ่มงานไม่ได้ กรุณากดรีเฟรชและตรวจรายการก่อนเพิ่มซ้ำ');}const created=toTask(item,this.columns);try{return await this.update({...created,no:String(item.id)},created);}catch{return created;}}
}
export async function createAuth(config){
  if(!config.clientId)return null;
  const app=new PublicClientApplication({auth:{clientId:config.clientId,authority:`https://login.microsoftonline.com/${config.tenantId}`,redirectUri:location.origin+'/',postLogoutRedirectUri:location.origin+'/'},cache:{cacheLocation:'sessionStorage'}});
  await app.initialize();const result=await app.handleRedirectPromise();let account=result?.account||app.getActiveAccount()||app.getAllAccounts()[0];
  function validate(a){if(!a)return;const email=a.idTokenClaims?.preferred_username||a.username||'';if(a.tenantId!==config.tenantId||!email.toLowerCase().endsWith('@'+config.allowedDomain))throw Error('กรุณาใช้บัญชี @askme.co.th ของบริษัทเท่านั้น');}
  validate(account);if(account)app.setActiveAccount(account);
  return {get account(){return app.getActiveAccount();},async login(){await app.loginRedirect({scopes:config.scopes,prompt:'select_account'});},async token(){const current=app.getActiveAccount();validate(current);if(!current)throw Error('กรุณาเข้าสู่ระบบก่อน');try{return (await app.acquireTokenSilent({scopes:config.scopes,account:current})).accessToken;}catch(e){if(e instanceof InteractionRequiredAuthError)throw new GraphError('กรุณาเข้าสู่ระบบอีกครั้งเพื่ออนุมัติการเชื่อมต่อ Microsoft',401);throw e;}},async logout(){await app.logoutRedirect({account:app.getActiveAccount()});}};
}
