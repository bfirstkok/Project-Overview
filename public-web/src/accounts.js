const fields=['project','task','priority','status','start','end','progress','sales','engineer','notes'];
export async function request(path,method='GET',data,headers={}){
 const response=await fetch(path,{method,credentials:'same-origin',cache:'no-store',headers:{...(data!==undefined?{'Content-Type':'application/json'}:{}),...headers},...(data!==undefined?{body:JSON.stringify(data)}:{})});
 const result=await response.json();if(!response.ok){const error=new Error(result.error||'ดำเนินการไม่สำเร็จ');error.status=response.status;throw error;}return result;
}
export class TaskStore{
 base=true;
 async load(){return (await request('/api/tasks')).tasks;}
 async create(task){return (await request('/api/tasks','POST',{requestId:crypto.randomUUID(),task:Object.fromEntries(fields.map(k=>[k,task[k]]))})).task;}
 async update(task,original){return (await request('/api/tasks/'+original.id,'PATCH',Object.fromEntries(fields.map(k=>[k,task[k]])),{'If-Match':original.etag})).task;}
}
export async function createAuth(){const {user}=await request('/api/session');return {account:user,async login(username,password){this.account=(await request('/api/login','POST',{username,password})).user;},async logout(){await request('/api/logout','POST');this.account=null;}};}
