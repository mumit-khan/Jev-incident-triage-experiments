'use strict';
function showStatus(message) {
 const status=document.getElementById('reader-status');
 status.textContent=message;status.classList.add('visible');
 setTimeout(()=>status.classList.remove('visible'),2500);
}
function highlightJson(code) {
 const original=code.textContent;
 const regex=/"(?:\\.|[^"\\])*"\s*:|"(?:\\.|[^"\\])*"|\b(?:true|false|null)\b|-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/g;
 const parts=[];let end=0;
 for(const match of original.matchAll(regex)) {
  parts.push(document.createTextNode(original.slice(end,match.index)));
  const span=document.createElement('span');
  span.className=match[0].endsWith(':')?'json-key':match[0].startsWith('"')?'json-string':'json-value';
  span.textContent=match[0];parts.push(span);end=match.index+match[0].length;
 }
 parts.push(document.createTextNode(original.slice(end)));code.replaceChildren(...parts);
}
document.querySelectorAll('.language-json').forEach(highlightJson);
document.querySelectorAll('[data-copy-code]').forEach(button=>button.addEventListener('click',async()=>{
 const code=button.closest('.code-example').querySelector('code').textContent;
 try{await navigator.clipboard.writeText(code);button.textContent='Copied';showStatus('Code copied');setTimeout(()=>button.textContent='Copy code',1800);}
 catch{const dialog=document.getElementById('copy-dialog'),text=document.getElementById('copy-text');text.value=code;dialog.showModal();text.focus();text.select();}
}));
document.getElementById('close-copy').addEventListener('click',()=>document.getElementById('copy-dialog').close());
const tableDialog=document.getElementById('table-dialog');
document.querySelectorAll('[data-expand-table]').forEach(button=>button.addEventListener('click',()=>{
 const wrapper=button.closest('.reading-table');
 let heading=wrapper.previousElementSibling;
 while(heading&&!['H2','H3'].includes(heading.tagName))heading=heading.previousElementSibling;
 document.getElementById('table-dialog-title').textContent=heading?.textContent||'Study comparison';
 document.getElementById('expanded-table').replaceChildren(wrapper.querySelector('table').cloneNode(true));
 tableDialog.showModal();document.getElementById('close-table').focus();
}));
document.getElementById('close-table').addEventListener('click',()=>tableDialog.close());
function showTableHints(){document.querySelectorAll('.reading-table').forEach(wrapper=>{const scroll=wrapper.querySelector('.table-scroll');wrapper.querySelector('.scroll-hint').hidden=scroll.scrollWidth<=scroll.clientWidth;});}
showTableHints();window.addEventListener('resize',showTableHints);
const select=document.getElementById('section-select');
select.addEventListener('change',()=>{if(select.value){location.hash=select.value;document.getElementById(select.value)?.scrollIntoView();}});
const headings=[...document.querySelectorAll('article h2[id],article h3[id]')];
const links=[...document.querySelectorAll('.contents nav a')];
function markSection() {
 let active=headings[0];
 for(const heading of headings){if(heading.getBoundingClientRect().top<=170)active=heading;else break;}
 for(const link of links){const current=link.hash==='#'+active?.id;link.classList.toggle('active',current);if(current)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');}
 if(active)select.value=active.id;
}
let ticking=false;window.addEventListener('scroll',()=>{if(!ticking){ticking=true;requestAnimationFrame(()=>{markSection();ticking=false;});}},{passive:true});markSection();
