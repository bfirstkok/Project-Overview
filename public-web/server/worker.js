import {api} from './api.js';
import assets from '../.local/assets.js';
export default {async fetch(request,env){
 const url=new URL(request.url);
 if(url.pathname.startsWith('/api/'))return api(request,env);
 const asset=assets[url.pathname==='/'?'/index.html':url.pathname];
 const headers={'Content-Type':asset?.type||'text/plain; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','X-Frame-Options':'DENY','Permissions-Policy':'camera=(), microphone=(), geolocation=()','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://login.microsoftonline.com; frame-src 'self' https://login.microsoftonline.com; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"};
 if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405,headers});
 return new Response(request.method==='HEAD'?null:asset?.body||'Not found',{status:asset?200:404,headers});
}};
