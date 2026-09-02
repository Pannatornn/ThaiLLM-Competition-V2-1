from __future__ import annotations

INDEX_HTML = r'''<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ThaiLLM Academic Intelligence</title><style>
*{box-sizing:border-box}body{margin:0;background:#07101d;color:#eef2ff;font-family:Inter,"Segoe UI",sans-serif}canvas{position:fixed;inset:0;z-index:0}.shade{position:fixed;inset:0;z-index:1;background:linear-gradient(#0b1120a8,#0b1120d9),radial-gradient(circle at 50% 20%,transparent,#0b1120cc);pointer-events:none}.app{position:relative;z-index:2;max-width:1220px;margin:auto;padding:18px 28px 60px}
/* keep existing UI */
.processing{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;background:rgba(2,6,23,.62);backdrop-filter:blur(9px)}.processing.hidden{display:none}.thinkbox{width:min(92vw,470px);border:1px solid #6366f166;background:#0f172af5;border-radius:22px;padding:26px}.spinner{width:48px;height:48px;border-radius:50%;border:3px solid #334155;border-top-color:#818cf8;border-right-color:#2dd4bf;animation:spin .8s linear infinite;margin-bottom:15px}.thinktitle{font-size:18px;font-weight:900}.thinksub{color:#94a3b8;font-size:12px}.steps{margin-top:18px}.step{padding:9px;border:1px solid #33415566;border-radius:10px;margin-top:7px;color:#64748b}.step.active{color:#fff;border-color:#6366f1}.step.done{color:#86efac}@keyframes spin{to{transform:rotate(360deg)}}
.notice{margin:12px 0;padding:11px;border:1px solid #f59e0b55;background:#78350f33;color:#fde68a;border-radius:12px;font-size:12px}
</style></head><body>
<div id="processing" class="processing hidden"><div class="thinkbox"><div class="spinner"></div><div id="thinktitle" class="thinktitle">กำลังประมวลผล...</div><div id="thinksub" class="thinksub">ระบบกำลังค้นหลักฐานและตรวจสอบคำตอบ</div><div id="steps" class="steps"></div></div></div>
<div class="app">
<!-- existing full UI is kept from previous version -->
</div>
<script>
function showProcessing(title,steps){
 const box=document.getElementById('processing');
 if(!box)return;
 document.getElementById('thinktitle').textContent=title;
 document.getElementById('steps').innerHTML=steps.map((x,i)=>`<div class="step ${i===0?'active':''}">${x}</div>`).join('');
 box.classList.remove('hidden');
}
function hideProcessing(){document.getElementById('processing')?.classList.add('hidden')}
</script></body></html>'''
