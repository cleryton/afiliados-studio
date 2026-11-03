'use strict';
let token='',current=null,permitUpload=false;
const el=id=>document.getElementById(id);
async function request(path,body){const r=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Studio-Token':token},body:JSON.stringify(body)});const v=await r.json();if(!r.ok)throw Error(v.error||'Operação não confirmada.');return v;}
function render(){
 if(!current)return;
 el('count').textContent=`${current.confirmed||0} de ${current.total||0} agendamentos confirmados; ${current.ready||0} MP4s locais disponíveis; ${current.archived||0} retirados.`;
 el('target').textContent=current.handle?`Perfil exclusivo: @${current.handle}`:(current.message||'Indisponível.');
 el('title').textContent=current.item?.title||'Nenhum horário pendente.';
 el('due').value=current.item?.due_at||'';el('file').value=current.file||'';el('caption').value=current.caption||'';
 const stage=current.attempt?.stage||'sem_reserva';el('stage').textContent=({sem_reserva:'Aguardando preparação',reserved:'Vídeo reservado',upload_started:'Upload registrado',details_checked:'Prévia conferida',submission_started:'Solicitação registrada',uncertain:'Conferir pedido incerto',confirmed:'Agendamento confirmado'})[stage]||'Conferir situação';el('hold').disabled=!current.attempt||stage==='confirmed';
 el('begin').disabled=!current.file||current.paused||Boolean(current.attempt);
 el('upload').disabled=!permitUpload||stage!=='reserved';
 el('details').disabled=stage!=='upload_started';el('submit').disabled=stage!=='details_checked';
 el('confirm').disabled=!['submission_started','uncertain'].includes(stage);
}
async function refresh(){current=await request('/api/stories/native/operator-state');permitUpload=false;render();}
async function action(button,fn){button.disabled=true;el('result').textContent='Processando…';try{await fn();}catch(error){el('result').textContent=error.message;el('permission').textContent='Retido para conferência; não repetir upload ou solicitação.';}finally{render();}}
function requireCheck(id){if(!el(id).checked)throw Error('Marque somente as observações que você realmente conferiu.');}
el('begin').onclick=()=>action(el('begin'),async()=>{requireCheck('profile');const v=await request('/api/stories/native/begin',{media_id:current.item.media_id,observed_handle:current.handle});current.attempt={id:v.id,stage:v.stage};permitUpload=v.may_upload===true;el('permission').textContent=permitUpload?'Permitido um único upload.':'Nenhum novo upload autorizado. Confira o pedido existente.';el('result').textContent='Reserva registrada.';});
el('upload').onclick=()=>action(el('upload'),async()=>{if(!permitUpload)throw Error('Nenhum novo upload autorizado.');await request('/api/stories/native/advance',{id:current.attempt.id,stage:'upload_started',observed_handle:current.handle});permitUpload=false;current.attempt.stage='upload_started';el('permission').textContent='Início registrado. Uma única seleção do arquivo original; não retransmitir.';el('result').textContent='Início do upload registrado.';});
el('details').onclick=()=>action(el('details'),async()=>{for(const k of ['caption-ok','ai-ok','public-ok','date-ok','checks-ok'])requireCheck(k);await request('/api/stories/native/advance',{id:current.attempt.id,stage:'details_checked',observed_handle:current.handle,due_at:current.item.due_at,caption_matches:true,ai_label:true,public_visibility:true,checks_clear:true});current.attempt.stage='details_checked';el('result').textContent='Conferência da prévia registrada.';});
el('submit').onclick=()=>action(el('submit'),async()=>{const v=await request('/api/stories/native/advance',{id:current.attempt.id,stage:'submission_started',observed_handle:current.handle,due_at:current.item.due_at,caption_matches:true,ai_label:true,public_visibility:true,checks_clear:true});current.attempt.stage='submission_started';el('permission').textContent=v.may_dispatch===true?'Permitido um único clique em Agendar no TikTok.':'Nenhum clique autorizado. Confira a lista sem repetir.';el('result').textContent='Solicitação registrada.';});
el('confirm').onclick=()=>action(el('confirm'),async()=>{requireCheck('reloaded');await request('/api/stories/native/confirm',{id:current.attempt.id,url:el('url').value,due_at:current.item.due_at,destination_reloaded:true,caption_matches:true});current.attempt.stage='confirmed';el('result').textContent='Recibo observado salvo. Publicação efetiva ainda não confirmada.';});
el('retire').onclick=()=>action(el('retire'),async()=>{requireCheck('retire-approved');const v=await request('/api/stories/local-archive/recycle-confirmed',{approved:true});el('result').textContent=`${v.recycled} MP4s confirmados retirados para a Lixeira.`;});
el('hold').onclick=()=>action(el('hold'),async()=>{await request('/api/stories/native/hold',{id:current.attempt.id,reason:'unconfirmed'});current.attempt.stage='uncertain';el('result').textContent='Pedido retido. Confira a prévia ou a lista do TikTok sem reenviar.';});
el('refresh').onclick=()=>action(el('refresh'),async()=>{for(const k of ['profile','caption-ok','ai-ok','public-ok','date-ok','checks-ok','reloaded'])el(k).checked=false;el('url').value='';el('permission').textContent='';await refresh();el('result').textContent='Próximo horário carregado.';});
(async()=>{try{const session=await request('/api/state');token=session.token;await refresh();el('result').textContent='Pronto para conferir o próximo horário.';}catch(error){el('result').textContent=error.message;}})();
