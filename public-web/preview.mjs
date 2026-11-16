import {createServer} from 'node:http';
import worker from './dist/server/index.js';
import {database} from './tests/d1.mjs';
import {demoTasks} from './src/demo.js';
const env={DB:database(),SETUP_TOKEN:'local-qa-only'};
const origin='http://127.0.0.1:5190';
for(const [path,data] of [['seed',{tasks:demoTasks().map((t,i)=>({...t,no:i+1})),sourceHash:'synthetic-qa-only',sourceFile:'synthetic-qa'}],['activate',{password:'local-qa-only-password'}]]){const response=await worker.fetch(new Request(origin+'/api/setup/'+path,{method:'POST',headers:{Origin:origin,'X-Setup-Token':env.SETUP_TOKEN},body:JSON.stringify(data)}),env);if(!response.ok)throw Error(await response.text());}
createServer(async(req,res)=>{try{const chunks=[];for await(const c of req)chunks.push(c);const response=await worker.fetch(new Request(origin+req.url,{method:req.method,headers:req.headers,...(!['GET','HEAD'].includes(req.method)?{body:Buffer.concat(chunks)}:{})}),env);res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));}catch{res.writeHead(500);res.end('Preview error');}}).listen(5190,'127.0.0.1',()=>console.log('Local QA http://127.0.0.1:5190 (synthetic data only)'));
