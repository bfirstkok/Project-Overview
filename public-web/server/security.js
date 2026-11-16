const encoder=new TextEncoder();
export const randomToken=()=>Array.from(crypto.getRandomValues(new Uint8Array(32)),n=>n.toString(16).padStart(2,'0')).join('');
export async function digest(value){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',encoder.encode(value))),n=>n.toString(16).padStart(2,'0')).join('');}
export async function hashPassword(password,salt){const material=await crypto.subtle.importKey('raw',encoder.encode(password),'PBKDF2',false,['deriveBits']);const bytes=await crypto.subtle.deriveBits({name:'PBKDF2',hash:'SHA-256',salt:encoder.encode(salt),iterations:100000},material,256);return Array.from(new Uint8Array(bytes),n=>n.toString(16).padStart(2,'0')).join('');}
export function timingEqual(a,b){if(typeof a!=='string'||typeof b!=='string')return false;let difference=a.length^b.length;for(let i=0;i<Math.max(a.length,b.length);i++)difference|=(a.charCodeAt(i)||0)^(b.charCodeAt(i)||0);return difference===0;}
export const cookieToken=request=>{const cookie=request.headers.get('Cookie')||'';return cookie.split(';').map(s=>s.trim()).find(s=>s.startsWith('workboard_session='))?.slice(18)||'';};
export function sessionCookie(token,request,clear=false){return `workboard_session=${clear?'':token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${clear?0:604800}${new URL(request.url).protocol==='https:'?'; Secure':''}`;}
