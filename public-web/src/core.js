export const STATUSES=['To Do','In Progress','On Hold','Complete','Cancelled'];
export const PRIORITIES=['Low','Normal','High','Critical'];
export const ROSTER={sales:['Panithan','Araya','Sabaipair','khanathippakorn'],engineer:['Jakkarin','Sayan','khanathippakorn']};
export function rosterFromUsers(users){return {sales:users.filter(u=>['sales','intern'].includes(u.role)).map(u=>u.name),engineer:users.filter(u=>['engineer','intern'].includes(u.role)).map(u=>u.name)};}
export const LABELS={no:'No',project:'Project Name',task:'Task',priority:'PRIORITY',status:'STATUS',start:'START DATE',end:'END DATE',progress:'% COMPLETE',sales:'Sales',engineer:'Engineer',notes:'NOTES to Colleague'};
export const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function people(value,kind,roster=ROSTER){let names=Array.isArray(value)?value:String(value||'').split(/\s*(?:;#|[,&/\n])\s*/);return [...new Set(names.flatMap(n=>n.trim().toUpperCase()==='ALL'&&kind==='engineer'?roster.engineer:[n.trim().toLowerCase()==='khanathippakorn'?'khanathippakorn':n.trim()]).filter(Boolean))];}
export function mapColumns(columns){const result={};for(const [key,label] of Object.entries(LABELS)){const col=columns.find(c=>c.displayName.trim().toLowerCase()===label.toLowerCase());if(!col)throw Error(`ไม่พบคอลัมน์ ${label} ใน Lists`);result[key]=col;}return result;}
export function toTask(item,columns){const f=item.fields||{};const value=k=>f[columns[k].name];return {id:String(item.id),etag:item.eTag||item['@odata.etag']||f['@odata.etag'],no:String(value('no')||''),project:String(value('project')||''),task:String(value('task')||''),priority:value('priority')||'Normal',status:value('status')||'To Do',start:(value('start')||'').slice(0,10),end:(value('end')||'').slice(0,10),progress:Math.round(Number(value('progress')||0)*100),sales:people(value('sales'),'sales'),engineer:people(value('engineer'),'engineer'),notes:String(value('notes')||'')};}
export function today(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Bangkok',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
export const effectiveStatus=t=>Number(t.progress)===100&&t.status!=='Cancelled'?'Complete':t.status;
export const withCompletion=t=>({...t,status:effectiveStatus(t)});
export const completed=t=>effectiveStatus(t)==='Complete';
export const pending=t=>!['Complete','Cancelled'].includes(effectiveStatus(t));
export const active=pending;
export const overdue=(t,day=today())=>Boolean(t.end&&t.end<day&&active(t));
export function filterTasks(tasks, {
  search = '', status = '', priority = '', person = '', scope = 'all', day = today(),
  progressMin = 0, progressMax = 100, assignedTeam = '',
} = {}) {
  const query = search.trim().toLocaleLowerCase();
  return tasks.filter(task =>
    (!query || `${task.no} ${task.project} ${task.task} ${task.notes}`.toLocaleLowerCase().includes(query)) &&
    (!status || effectiveStatus(task) === status) &&
    (!priority || task.priority === priority) &&
    (!person || [...task.sales, ...task.engineer].includes(person)) &&
    (!assignedTeam || task[assignedTeam]?.length > 0) &&
    ((progressMin === 0 && progressMax === 100) || (task.progress >= progressMin && task.progress <= progressMax)) &&
    (scope !== 'pending' || pending(task)) &&
    (scope !== 'active' || active(task)) &&
    (scope !== 'overdue' || overdue(task, day)) &&
    (scope !== 'done' || completed(task))
  );
}
export function sortTasks(tasks,key='latest',descending=true){return [...tasks].sort((a,b)=>{const left=key==='latest'?Number(a.id):key==='no'?Number(a.no):a[key],right=key==='latest'?Number(b.id):key==='no'?Number(b.no):b[key];const cmp=typeof left==='number'?left-right:String(left??'').localeCompare(String(right??''),'th',{numeric:true});return (descending?-1:1)*cmp;});}
export function validateTask(t,original,roster=ROSTER){const errors=[];if(!t.project.trim())errors.push('กรุณาใส่ชื่อโครงการ');if(!t.task.trim())errors.push('กรุณาใส่รายละเอียดงาน');if(!STATUSES.includes(t.status))errors.push('สถานะไม่ถูกต้อง');if(!PRIORITIES.includes(t.priority))errors.push('Priority ไม่ถูกต้อง');if(!Number.isInteger(t.progress)||t.progress<0||t.progress>100)errors.push('ความคืบหน้าต้องอยู่ระหว่าง 0–100%');if(t.start&&t.end&&t.end<t.start&&(!original||t.start!==original.start||t.end!==original.end))errors.push('วันสิ้นสุดต้องไม่ก่อนวันเริ่มต้น');for(const kind of ['sales','engineer'])if(t[kind].some(n=>!roster[kind].includes(n)))errors.push(`รายชื่อ ${kind} ไม่อยู่ในทีม`);if(t.project.length>500||t.task.length>5000||t.notes.length>10000)errors.push('ข้อความยาวเกินกำหนด (โครงการ 500, งาน 5,000, บันทึก 10,000 ตัวอักษร)');return errors;}
export function toFields(t,columns,original){const result={};for(const key of Object.keys(LABELS)){if(original&&JSON.stringify(t[key])===JSON.stringify(original[key]))continue;const col=columns[key],name=col.name;let value=t[key];if(['sales','engineer'].includes(key)){if(!col.choice?.allowMultipleSelections)throw Error(`คอลัมน์ ${LABELS[key]} ต้องอนุญาตให้เลือกหลายคนก่อน`);result[`${name}@odata.type`]='Collection(Edm.String)';value=t[key];}else if(key==='progress')value=t.progress/100;else if(['start','end'].includes(key))value=t[key]?`${t[key]}T00:00:00Z`:null;result[name]=value;}return result;}
export const blankTask=()=>({no:'',project:'',task:'',priority:'Normal',status:'To Do',start:today(),end:'',progress:0,sales:[],engineer:[],notes:''});
export function metrics(tasks,day=today()){return {total:tasks.length,pending:tasks.filter(pending).length,active:tasks.filter(active).length,done:tasks.filter(completed).length,overdue:tasks.filter(t=>overdue(t,day)).length};}
