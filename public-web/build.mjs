import {build} from 'esbuild';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
await mkdir('dist/server',{recursive:true});await mkdir('.local',{recursive:true});
const browser=await build({entryPoints:['src/app.js'],bundle:true,format:'esm',minify:true,target:'es2022',write:false,legalComments:'eof'});
const assets={'/app.js':{type:'text/javascript; charset=utf-8',body:browser.outputFiles[0].text}};
for(const [file,type] of [['index.html','text/html'],['style.css','text/css'],['readable.css','text/css']])assets['/'+file]={type:type+'; charset=utf-8',body:await readFile('public/'+file,'utf8')};
await writeFile('.local/assets.js','export default '+JSON.stringify(assets)+';');
await build({entryPoints:['server/worker.js'],bundle:true,format:'esm',minify:true,target:'es2022',platform:'browser',outfile:'dist/server/index.js',legalComments:'eof'});
console.log('Built Workboard Worker with embedded public assets (no company data).');
