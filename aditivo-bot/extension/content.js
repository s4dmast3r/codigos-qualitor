
const $ = sel => document.querySelector(sel);
function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
window.alert = msg => { chrome.runtime.sendMessage({status:"fail", reason:msg}); };
const queue = []; let busy=false;
async function processNext(){
 if(busy||!queue.length) return; busy=true;
 const code = queue.shift();
 try{
   const input = $('input[placeholder="Código"]')||$('input[type="text"]');
   if(!input){ busy=false; return; }
   input.value=code; input.dispatchEvent(new Event('input',{bubbles:true}));
   const btn = document.querySelector('button svg[data-icon="check"]')?.closest('button');
   if(btn) btn.click();
   const t0=performance.now(); let ok=false;
   while(performance.now()-t0<8000){ await sleep(400);}
   chrome.runtime.sendMessage({status: ok?'ok':'fail', code});
 }finally{ busy=false; processNext(); }
}
chrome.runtime.onMessage.addListener(({code})=>{ queue.push(code); processNext(); });
