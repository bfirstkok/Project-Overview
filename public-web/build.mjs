import {build} from 'esbuild';
import {mkdir,copyFile} from 'node:fs/promises';
await mkdir('dist',{recursive:true});
await build({entryPoints:['src/app.js'],bundle:true,format:'esm',minify:true,target:'es2022',outfile:'dist/app.js',legalComments:'eof'});
for (const file of ['index.html','style.css','readable.css','config.json','_headers']) await copyFile(`public/${file}`,`dist/${file}`);
console.log('Built static Workboard');
