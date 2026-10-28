/* ParentBridge AI - no frontend framework, no CDN, no third-party tracking. */
'use strict';
const $ = (q) => document.querySelector(q);
const $$ = (q) => [...document.querySelectorAll(q)];
const app = { state: null, active: null, compose: 'parent', filter: 'all', view: 'inbox', term: '', token: '' };
const e = (s) => String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const titleCase = (s) => (s||'').replace(/\b\w/g, ch=>ch.toUpperCase());
let toastTimer;
function toast(message, error=false){const el=$('#toast');el.textContent=message;el.className=`toast show ${error?'error':''}`;clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),3500)}
async function api(path,opts={}){
 const headers = { 'Content-Type':'application/json', ...(app.token?{'x-admin-key':app.token}:{}), ...(opts.headers||{}) };
 const resp=await fetch(path,{...opts,headers});
 if(resp.status===401){
   const key=prompt('AWS mode is protected. Enter your admin API key (not stored on disk):');
   if(key && key!==app.token){app.token=key;return api(path,opts)}
   throw new Error('Admin key is required.');
 }
 let payload;try{payload=await resp.json()}catch{throw new Error('Network response was not JSON')}
 if(!resp.ok)throw new Error(payload.error || `HTTP ${resp.status}`);
 return payload;
}
function relative(iso){if(!iso)return '';const ms=Date.now()-new Date(iso).getTime();if(ms<3600000)return `${Math.max(1,Math.round(ms/60000))}m`;if(ms<86400000)return `${Math.round(ms/3600000)}h`;return new Date(iso).toLocaleDateString(undefined,{month:'short',day:'numeric'})}
function hhmm(iso){return new Date(iso).toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'})}
function currentContact(){return app.state?.contacts.find(c=>c.id===app.active)}
async function loadState(preferred=null){try{const contactId=preferred||app.active;app.state=await api('/api/state'+(contactId?`?contact_id=${encodeURIComponent(contactId)}`:''));app.active=app.state.active_contact;render()}catch(err){toast(err.message,true)}}
function render(){const s=app.state;if(!s)return;
 $('#metric-families').textContent=s.metrics.conversations;
 $('#metric-messages').textContent=s.metrics.messages;
 $('#metric-handoffs').textContent=s.metrics.handoffs;
 $('#metric-channels').textContent=s.metrics.channels;
 $('#nav-count').textContent=s.contacts.length;
 $('#convo-count').textContent=s.contacts.length;
 $('#side-ai').textContent=s.system.ai;
 $('#side-cds').textContent=s.system.delivery;
 $('#mode-label').textContent=s.system.mode==='AWS connected'?'AWS MODE · RESTRICTED':'SAFE DEMO MODE';
 renderContacts();renderThread();renderSubview();
}
function renderContacts(){const contacts=app.state.contacts.filter(c=>(app.filter!=='attention'||c.unresolved>0)&&`${c.name} ${c.role} ${c.child}`.toLowerCase().includes(app.term));
 if(!contacts.length){$('#contact-list').innerHTML='<p class="empty-placeholder">No matching conversations.</p>';return}
 $('#contact-list').innerHTML=contacts.map((c,i)=>`<button class="contact-row ${c.id===app.active?'current':''}" role="option" aria-selected="${c.id===app.active}" data-id="${e(c.id)}"><span class="person-avatar tone${i%4}">${e(c.initials)}</span><span class="contact-copy"><span class="contact-title"><strong>${e(c.name)}</strong><time>${e(relative(c.last_at))}</time></span><span class="contact-line">${e(c.last_message)}</span><span class="contact-footer"><span class="tiny-tag ${c.preferred_channel==='email'?'email':''}">${e(c.preferred_channel.toUpperCase())}</span>${e(c.role)}${c.unresolved>0?'<span class="attention-dot" title="Staff follow-up needed"></span>':''}</span></span></button>`).join('');
 $$('.contact-row').forEach(el=>el.addEventListener('click',()=>loadState(el.dataset.id)));
}
function renderThread(){const c=currentContact();if(!c){$('#messages').innerHTML='<p class="empty-placeholder">Add a contact to start.</p>';return}
 const tone=['maria','james','noura','oliver'].indexOf(c.id);const cls=`tone${Math.max(0,tone)%4}`;
 $('#chat-header').innerHTML=`<span class="person-avatar big ${cls}">${e(c.initials)}</span><div class="chat-person"><strong>${e(c.name)}</strong><small>${e(c.role)} · ${e(c.child)}</small></div><span class="thread-status">● ${e(titleCase(c.status||'active'))}</span>`;
 $('#profile').innerHTML=`<span class="person-avatar large ${cls}">${e(c.initials)}</span><h3>${e(c.name)}</h3><p>${e(c.role)}</p>`;
 $('#detail-email').textContent=c.email||'Not provided';$('#detail-phone').textContent=c.phone||'Not provided';
 $('#detail-channel').textContent=titleCase(c.preferred_channel||'None');
 const msgs=app.state.messages;
 if(!msgs.length){$('#messages').innerHTML='<p class="empty-placeholder">No messages yet. Start the conversation below.</p>'}
 else{$('#messages').innerHTML='<div class="date-divider">CONVERSATION HISTORY · SYNCED ACROSS CHANNELS</div>'+msgs.map(m=>`<div class="message-line ${m.direction==='outbound'?'outbound':'inbound'}">${m.direction==='inbound'?`<span class="msg-avatar">${e(c.initials)}</span>`:''}<div class="bubble"><p>${e(m.body)}</p><div class="bubble-foot"><span class="bubble-channel">${e(m.channel.toUpperCase())}</span><span>${e(hhmm(m.created_at))} ${m.handoff?'<span class="handoff-mark"> · HUMAN REVIEW</span>':''} ${m.status==='failed'?'<span class="handoff-mark"> · FAILED</span>':''}</span></div></div>${m.direction==='outbound'?'<span class="msg-avatar ai">✦</span>':''}</div>`).join('');}
 const last=[...msgs].reverse().find(m=>m.direction==='outbound');
 $('#intent-detail').textContent=last?(last.intent==='announcement'?'School-initiated update':`${titleCase(last.intent)} · ${last.engine==='amazon-bedrock'?'Amazon Bedrock':last.engine==='rules-preview'?'preview rules':last.engine}`):'Intent appears after a reply.';
 $('#handoff-detail').textContent=last?.handoff?'Staff review requested. No sensitive action was executed.':'Responses remain grounded; sensitive requests trigger staff review.';
 const channel=$('#channel');
 for(const opt of channel.options)opt.disabled=!(opt.value==='sms'?c.consent_sms&&c.phone:c.consent_email&&c.email);
 channel.value=c.preferred_channel||'email';if(channel.selectedOptions[0]?.disabled)channel.value=c.consent_email?'email':'sms';
 $('#send-button').disabled=![...channel.options].some(o=>!o.disabled);
 $('#messages').scrollTop=$('#messages').scrollHeight;
}
function setCompose(value){app.compose=value;$$('.mode-tab').forEach(btn=>btn.classList.toggle('active',btn.dataset.compose===value));
 $('#message-input').placeholder=value==='parent'?'Type a parent message to see the assistant respond...':'Write a school update to this family...';
 $('#composer-help').textContent=value==='parent'?'Preview an inbound reply using the selected channel.':'Create a consent-aware outbound announcement.';
 $('#message-input').focus();
}
function setView(view){app.view=view;app.filter=view==='attention'?'attention':'all';
 $$('.nav-item').forEach(btn=>btn.classList.toggle('selected',btn.dataset.view===view));
 $$('.filter').forEach(btn=>btn.classList.toggle('active',btn.dataset.filter===app.filter));
 const labels={inbox:['Conversations','Every conversation. One connected story.','A unified workspace where school and family communication flows naturally across channels.'],attention:['Needs attention','A human touch when it matters.','Sensitive requests get routed to staff instead of risking an unverified decision.'],audience:['Family directory','Every family, connected.','A consent-first contact directory with clear channel preferences.'],insights:['Insights','Signals that make service better.','Monitor conversations, channel adoption and human handoffs.']};
 const [crumb,title,desc]=labels[view];$('#breadcrumb-current').textContent=crumb;$('#view-title').innerHTML=e(title).replace(/\.$/,'<span class="period">.</span>');$('#view-desc').textContent=desc;
 $('#conversation-section').hidden=['audience','insights'].includes(view);
 $('#subview').hidden=!['audience','insights'].includes(view);
 renderContacts();renderSubview();
}
function renderSubview(){if(!app.state)return;const target=$('#subview');if(['inbox','attention'].includes(app.view)){target.innerHTML='';return}
 if(app.view==='audience'){
 target.innerHTML=`<h2>Consent-first family directory</h2><p>Every contact has a preferred channel and recorded opt-in status. Select a family to open their shared conversation history.</p><div class="directory-grid">${app.state.contacts.map(c=>`<button class="directory-card" data-directory="${e(c.id)}"><span class="person-avatar">${e(c.initials)}</span><span><strong>${e(c.name)}</strong><small>${e(c.email||'No email')}</small><small>${e(c.preferred_channel.toUpperCase())} preferred · ${c.consent_email?'Email opted in':'Email off'} · ${c.consent_sms?'SMS opted in':'SMS off'}</small></span></button>`).join('')}</div>`;
 $$('[data-directory]').forEach(btn=>btn.addEventListener('click',()=>{setView('inbox');loadState(btn.dataset.directory)}));
 } else {
 const m=app.state.metrics;
 target.innerHTML=`<h2>Conversation intelligence</h2><p>All figures are computed from the currently stored message history. No fabricated conversion rates or delivery claims.</p><div class="insight-bars"><div class="insight-bar"><span>Conversations served</span><strong>${m.conversations}</strong><div class="bar"></div></div><div class="insight-bar"><span>Messages exchanged</span><strong>${m.messages}</strong><div class="bar"></div></div><div class="insight-bar"><span>Staff handoffs flagged</span><strong>${m.handoffs}</strong><div class="bar"></div></div></div><p style="margin-top:30px">Architecture: Amazon SES + AWS End User Messaging SMS → SNS → Lambda → Bedrock + DynamoDB → opted-in reply channel. This is a local simulation unless AWS mode is deployed and configured.</p>`;
 }
}
async function sendMessage(ev){ev.preventDefault();const c=currentContact();if(!c)return;
 const input=$('#message-input');const text=input.value.trim();if(!text)return;
 const channel=$('#channel').value;const btn=$('#send-button');btn.disabled=true;
 try{
 const path=app.compose==='parent'?'/api/message':'/api/announce';
 await api(path,{method:'POST',body:JSON.stringify({contact_id:c.id,channel,text})});input.value='';
 await loadState(c.id);toast(app.compose==='parent'?'Parent reply processed with cross-channel context.':'Announcement queued for approved channel.');
 }catch(err){toast(err.message,true)}finally{btn.disabled=false;input.focus()}
}
function init(){
 $('#composer').addEventListener('submit',sendMessage);
 $('#message-input').addEventListener('keydown',ev=>{if(ev.key==='Enter'&&!ev.shiftKey){ev.preventDefault();$('#composer').requestSubmit()}});
 $$('.mode-tab').forEach(b=>b.addEventListener('click',()=>setCompose(b.dataset.compose)));
 $$('.nav-item').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
 $$('.filter').forEach(b=>b.addEventListener('click',()=>{app.filter=b.dataset.filter;$$('.filter').forEach(v=>v.classList.toggle('active',v.dataset.filter===app.filter));renderContacts()}));
 $('#contact-search').addEventListener('input',ev=>{app.term=ev.target.value.toLowerCase();renderContacts()});
 $('#reload-button').addEventListener('click',()=>loadState());$('#list-refresh').addEventListener('click',()=>loadState());
 $('#new-contact').addEventListener('click',()=>$('#contact-dialog').showModal());
 $('#close-dialog').addEventListener('click',()=>$('#contact-dialog').close());
 $('#contact-form').addEventListener('submit',async ev=>{ev.preventDefault();const f=new FormData(ev.target);const data={name:f.get('name'),email:f.get('email'),phone:f.get('phone'),preferred_channel:f.get('preferred_channel'),consent_email:f.has('consent_email'),consent_sms:f.has('consent_sms')};try{const result=await api('/api/contacts',{method:'POST',body:JSON.stringify(data)});$('#contact-dialog').close();ev.target.reset();setView('inbox');await loadState(result.contact.id);toast('New contact created.')}catch(err){toast(err.message,true)}});
 $('#about-button').addEventListener('click',()=>$('#info-dialog').showModal());
 $('#close-info').addEventListener('click',()=>$('#info-dialog').close());
 $('#info-close-button').addEventListener('click',()=>$('#info-dialog').close());
 loadState();
}
window.addEventListener('DOMContentLoaded',init);
