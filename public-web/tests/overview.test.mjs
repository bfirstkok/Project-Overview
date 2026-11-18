import test from 'node:test';
import assert from 'node:assert/strict';
import {overviewData} from '../src/overview.js';
const day='2026-11-18',base={status:'In Progress',progress:50,priority:'High',start:'2026-11-01',end:'2026-11-17',sales:['New Intern'],engineer:['New Intern']},users=[{name:'New Intern',role:'intern'},{name:'New Sales',role:'sales'}];
test('overview statuses reconcile to tasks, completion remains explicit, and multi-team assignments count once per employee',()=>{
 const tasks=[base,{...base,progress:100},{...base,status:'Complete'},{...base,status:'Cancelled'},{...base,end:day,priority:'Normal',sales:['New Sales'],engineer:[]}],before=JSON.stringify(tasks),data=overviewData(tasks,users,day);
 assert.equal(data.statuses.reduce((n,s)=>n+s.count,0),tasks.length);assert.equal(data.statuses.find(s=>s.status==='In Progress').count,3);assert.equal(data.metrics.ready,1);assert.equal(data.metrics.overdue,1);
 assert.equal(data.priorities.find(p=>p.priority==='High').count,1);assert.equal(data.priorities.find(p=>p.priority==='Normal').count,1);
 const intern=data.workload.find(p=>p.name==='New Intern');assert.deepEqual({normal:intern.normal,late:intern.late,ready:intern.ready,total:intern.total},{normal:0,late:1,ready:1,total:2});assert.equal(data.workload.find(p=>p.name==='New Sales').normal,1);assert.equal(JSON.stringify(tasks),before);
});
test('six-month chart uses Start Date and calendar boundaries without inventing completion dates',()=>{
 const data=overviewData([{...base,start:'2025-08-02'},{...base,start:'2026-01-01'},{...base,start:'2025-07-31'},{...base,start:''}],users,'2026-01-04');assert.deepEqual(data.months.map(m=>m.key),['2025-08','2025-09','2025-10','2025-11','2025-12','2026-01']);assert.equal(data.months[0].count,1);assert.equal(data.months[5].count,1);assert.equal(data.months.reduce((n,m)=>n+m.count,0),2);assert.equal(data.missingStart,1);
});
test('empty overview preserves zero categories and unassigned employees without invalid values',()=>{
 const data=overviewData([],users,day);assert.equal(data.metrics.total,0);assert.ok(data.statuses.every(s=>s.count===0));assert.ok(data.priorities.every(s=>s.count===0));assert.ok(data.months.every(s=>s.count===0));assert.equal(data.workload.length,2);assert.ok(data.workload.every(p=>p.total===0));
});
