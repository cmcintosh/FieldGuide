// SPDX-License-Identifier: GPL-2.0-only
'use strict';
const $ = id => document.getElementById(id);
function el(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
async function api(path, payload) {
  const options = payload === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-Field-Library':'1'}, body:JSON.stringify(payload)};
  const response = await fetch(path, options); const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Local request failed'); return result;
}
function guard(fn) { return async event => { $('global-error').textContent = ''; try { await fn(event); } catch (error) { $('global-error').textContent = error.message; } }; }
function formValues(form) { return Object.fromEntries(new FormData(form).entries()); }
async function status() {
  const result = await api('/api/status'); $('connection').textContent = 'Local service available';
  $('ai-state').textContent = result.ai_enabled ? 'Local AI configured' : 'Source search mode · AI disabled';
  $('stats').replaceChildren(...['documents','chunks','inventory','notes'].map(name => { const node=el('span',undefined,'metric'); node.append(el('strong',String(result[name])),el('span',name)); return node; }));
}
async function openDocument(id) {
  const doc = await api('/api/document?id='+encodeURIComponent(id)); $('document-title').textContent=doc.title;
  $('document-meta').textContent=`${doc.source} · ${doc.license} · ${doc.updated}`; $('document-text').textContent=doc.text;
  $('document').hidden=false; $('document').scrollIntoView({behavior:'smooth'});
}
function renderSources(sources) {
  $('sources').replaceChildren();
  if (!sources.length) { $('sources').append(el('p','No matching documents. Try different words or add a relevant source.','empty')); return; }
  for (const source of sources) {
    const card=el('article',undefined,'source'); const link=el('button',`${source.citation ? '['+source.citation+'] ' : ''}${source.title}`);
    link.addEventListener('click',guard(()=>openDocument(source.doc_id))); card.append(link);
    card.append(el('p',`${source.source} · ${source.license} · ${source.updated}`,'muted'));
    card.append(el('p',source.excerpt || source.text,'excerpt')); $('sources').append(card);
  }
}
document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',guard(async()=>{
  document.querySelectorAll('.tab').forEach(node=>node.hidden=node.id!==button.dataset.tab);
  document.querySelectorAll('[data-tab]').forEach(node=>node.setAttribute('aria-selected',String(node===button)));
  $('document').hidden=true;
  if(button.dataset.tab==='supplies') await loadInventory();
  if(button.dataset.tab==='notes') await loadNotes();
})));
$('ask-form').addEventListener('submit',guard(async event=>{
  event.preventDefault(); const button=$('ask-button'); button.disabled=true; button.textContent='Reading local sources…';
  try {
    const result=await api('/api/ask',{question:$('question').value}); $('answer').hidden=false;
    $('answer-mode').textContent=result.mode.replaceAll('_',' '); $('answer-text').textContent=result.answer;
    $('answer-notice').textContent=result.notice || result.detail || ''; renderSources(result.sources);
  } finally {button.disabled=false; button.textContent='Ask the library';}
}));
$('search-button').addEventListener('click',guard(async()=>{
  $('answer').hidden=true; renderSources(await api('/api/search?q='+encodeURIComponent($('question').value)));
}));
$('close-document').addEventListener('click',()=>$('document').hidden=true);
$('text-file').addEventListener('change',guard(async event=>{
  const file=event.target.files[0]; if(!file)return;
  if(file.size>2_000_000)throw new Error('Split files larger than 2 MB before importing.');
  $('import-form').elements.text.value=await file.text();
  if(!$('import-form').elements.title.value)$('import-form').elements.title.value=file.name;
}));
$('import-form').addEventListener('submit',guard(async event=>{
  event.preventDefault(); const result=await api('/api/import',{documents:[formValues(event.target)]});
  $('import-result').textContent=result.imported ? 'Document saved and indexed.' : 'This document was already imported.';
  await status();
}));
async function loadInventory(){
  const items=await api('/api/inventory'); $('inventory-list').replaceChildren(); let total=0;
  for(const item of items){ const card=el('article',undefined,'source'); card.append(el('h3',item.name));
    card.append(el('p',`${item.quantity} ${item.unit} · ${item.location || 'No location'} · Expires: ${item.expires || 'not entered'}`));
    $('inventory-list').append(card); total+=item.quantity*item.calories_per_unit; }
  $('inventory-total').textContent=`${items.length} entries · ${Math.round(total).toLocaleString()} entered calories total`;
}
$('inventory-form').addEventListener('submit',guard(async event=>{
  event.preventDefault(); await api('/api/inventory',formValues(event.target)); event.target.reset(); await loadInventory(); await status();
}));
async function loadNotes(){
  $('note-list').replaceChildren(); for(const note of await api('/api/notes')){
    const card=el('article',undefined,'source'); card.append(el('h3',note.title),el('p',note.text,'prose')); $('note-list').append(card);
  }
}
$('note-form').addEventListener('submit',guard(async event=>{
  event.preventDefault(); await api('/api/notes',formValues(event.target)); event.target.reset(); await loadNotes(); await status();
}));
$('export-button').addEventListener('click',guard(async()=>{
  const backup=await api('/api/backup'); const blob=new Blob([JSON.stringify(backup,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob); const a=el('a'); a.href=url; a.download='field-library-backup-'+new Date().toISOString().slice(0,10)+'.json';
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);
}));
$('restore-button').addEventListener('click',guard(async()=>{
  const file=$('backup-file').files[0]; if(!file)throw new Error('Select a backup first.');
  if(file.size>7_000_000)throw new Error('Use the CLI restore command for backups larger than 7 MB.');
  const result=await api('/api/restore',JSON.parse(await file.text()));
  $('backup-result').textContent=`Merged backup; ${result.documents_imported} new documents. Inventory and notes appended.`;await status();
}));
guard(status)();
