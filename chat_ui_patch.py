from __future__ import annotations


CHAT_RUNTIME_PATCH = r'''<script>
// Runtime fixes layered after the base UI so guest history never duplicates
// messages and follow-up questions can use recent conversation context.
openConversation = async function(id){
  const c=conversations.find(x=>x.id===id); if(!c)return;
  currentConversation=c; document.querySelector('#conversationTitle').textContent=c.title||'แชทใหม่';
  if(currentUser&&sb){
    const {data,error}=await sb.from('messages').select('*').eq('conversation_id',id).order('created_at',{ascending:true});
    messages=error?[]:(data||[]);
  }else{
    // Copy rather than alias c.messages. persistMessage writes to both the
    // visible thread and stored conversation; aliasing caused duplicates.
    messages=[...(c.messages||[])];
  }
  renderHistory(document.querySelector('#searchChats').value); renderMessages();
  document.querySelector('#sidebar').classList.remove('open');
};

sendMessage = async function(){
  const ta=document.querySelector('#composer'),q=ta.value.trim(); if(!q)return;
  ta.value=''; autoSize(); document.querySelector('#sendBtn').disabled=true;
  try{
    await ensureConversation(q);
    // Snapshot context before appending the new question twice.
    const history=messages.slice(-10).map(m=>({role:m.role,content:m.content}));
    await persistMessage('user',q,{}); renderMessages(); addThinking();
    const r=await fetch('/api/chat',{method:'POST',headers:apiHeaders(),body:JSON.stringify({question:q,history})});
    const d=await r.json(); removeThinking();
    const answer=d.answer||d.answerTh||d.error||'ไม่สามารถสร้างคำตอบได้';
    await persistMessage('assistant',answer,{
      status:d.status||'', language:d.language||'', programDetected:d.programDetected||'',
      confidence:d.confidence??0, evidenceList:d.evidenceList||[], modelDisplay:d.modelDisplay||'',
      contextualized:Boolean(d.contextualized)
    });
    renderMessages();
  }catch(e){
    removeThinking();
    messages.push({id:uid(),role:'assistant',content:'เกิดข้อผิดพลาด: '+(e.message||e),metadata:{status:'ERROR'}});
    renderMessages();
  }finally{document.querySelector('#sendBtn').disabled=false;ta.focus()}
};
</script>'''


def inject_chat_runtime_patch(html: str) -> str:
    return html.replace("</body>", CHAT_RUNTIME_PATCH + "\n</body>", 1)
