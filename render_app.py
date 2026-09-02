from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

import render_server as core

PROCESS_CSS = r'''
.processing-overlay{position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;background:rgba(2,6,23,.68);backdrop-filter:blur(9px);-webkit-backdrop-filter:blur(9px)}
.processing-overlay.hidden{display:none}
.processing-card{width:min(92vw,470px);border:1px solid rgba(99,102,241,.5);background:linear-gradient(180deg,rgba(15,23,42,.98),rgba(8,15,29,.98));border-radius:22px;padding:26px;box-shadow:0 24px 80px rgba(0,0,0,.45)}
.processing-top{display:flex;align-items:center;gap:16px}.processing-spinner{width:48px;height:48px;flex:0 0 48px;border-radius:50%;border:3px solid rgba(71,85,105,.65);border-top-color:#818cf8;border-right-color:#2dd4bf;animation:processingSpin .85s linear infinite}.processing-title{font-size:18px;font-weight:900;color:#f8fafc}.processing-sub{margin-top:5px;color:#94a3b8;font-size:12px;line-height:1.5}.processing-steps{margin-top:18px;display:grid;gap:8px}.processing-step{display:flex;align-items:center;gap:9px;padding:9px 11px;border:1px solid rgba(51,65,85,.62);border-radius:10px;background:rgba(15,23,42,.55);color:#64748b;font-size:11px;transition:.25s}.processing-step .dot{width:8px;height:8px;border-radius:50%;background:#475569;box-shadow:0 0 0 3px rgba(71,85,105,.12)}.processing-step.active{color:#e0e7ff;border-color:rgba(99,102,241,.58);background:rgba(79,70,229,.12)}.processing-step.active .dot{background:#818cf8;box-shadow:0 0 14px rgba(129,140,248,.85)}.processing-step.done{color:#86efac;border-color:rgba(34,197,94,.28)}.processing-step.done .dot{background:#22c55e}.processing-time{margin-top:13px;color:#64748b;font:700 10px ui-monospace,Consolas,monospace;text-align:right}@keyframes processingSpin{to{transform:rotate(360deg)}}
@media(max-width:600px){.processing-card{padding:20px}.processing-title{font-size:16px}}
'''

PROCESS_HTML = r'''
<div id="processingOverlay" class="processing-overlay hidden" aria-live="polite" aria-busy="true">
  <div class="processing-card">
    <div class="processing-top">
      <div class="processing-spinner"></div>
      <div>
        <div id="processingTitle" class="processing-title">กำลังประมวลผล...</div>
        <div id="processingSub" class="processing-sub">ระบบกำลังค้นหลักฐานและตรวจสอบคำตอบ กรุณารอสักครู่</div>
      </div>
    </div>
    <div id="processingSteps" class="processing-steps"></div>
    <div id="processingTime" class="processing-time">0s</div>
  </div>
</div>
'''

PROCESS_JS = r'''
<script>
(()=>{
  if(window.__THAILLM_PROCESSING_PATCH__) return;
  window.__THAILLM_PROCESSING_PATCH__=true;

  const nativeFetch=window.fetch.bind(window);
  let timer=null, clock=null, started=0, currentStep=0, activeCount=0;

  const configs={
    '/api/ask':{
      th:['กำลังวิเคราะห์คำถาม...','ระบบกำลังค้นหลักฐานที่เกี่ยวข้องและให้ ThaiLLM สร้างคำตอบ'],
      en:['Analyzing your question...','Retrieving evidence and asking ThaiLLM to prepare a grounded answer.'],
      stepsTh:['วิเคราะห์คำถามและหลักสูตร','ค้นหา Evidence ที่เกี่ยวข้อง','ประมวลผลด้วย ThaiLLM','ตรวจสอบคำตอบก่อนแสดงผล'],
      stepsEn:['Analyze query and program','Retrieve relevant evidence','Process with ThaiLLM','Validate answer before display']
    },
    '/api/compare':{
      th:['กำลังเปรียบเทียบหลักสูตร...','ระบบกำลังรวบรวม canonical facts และ evidence จากทั้งสองหลักสูตร'],
      en:['Comparing programs...','Collecting canonical facts and balanced evidence from both programs.'],
      stepsTh:['อ่านประเด็นที่ต้องการเปรียบเทียบ','รวบรวมข้อมูลจากทั้งสองหลักสูตร','วิเคราะห์ความแตกต่าง','สร้างตารางและตรวจ Evidence'],
      stepsEn:['Read comparison focus','Collect both programs evidence','Analyze differences','Build table and verify evidence']
    },
    '/api/benchmark':{
      th:['กำลังรัน Judge Benchmark...','กำลังประเมินชุดทดสอบจริง อาจใช้เวลานานกว่าคำถามปกติ'],
      en:['Running Judge Benchmark...','Evaluating the real benchmark suite. This can take longer than a normal query.'],
      stepsTh:['เตรียมชุดทดสอบ Easy baseline','ประเมินคำถามทีละกรณี','ตรวจ Scope และ Injection','สรุป Accuracy และ Evidence metrics'],
      stepsEn:['Prepare Easy baseline suite','Evaluate benchmark cases','Check scope and injection','Aggregate accuracy and evidence metrics']
    }
  };

  function language(){
    const en=document.getElementById('en');
    return en && en.classList.contains('on') ? 'EN' : 'TH';
  }

  function endpointOf(input){
    try{
      const raw=typeof input==='string'?input:(input&&input.url)||'';
      const u=new URL(raw,window.location.origin);
      return Object.keys(configs).find(x=>u.pathname===x)||null;
    }catch(_){return null}
  }

  function renderSteps(items){
    const box=document.getElementById('processingSteps');
    if(!box) return;
    box.innerHTML=items.map((s,i)=>`<div class="processing-step ${i===0?'active':''}"><span class="dot"></span><span>${s}</span></div>`).join('');
  }

  function markStep(index){
    const nodes=[...document.querySelectorAll('.processing-step')];
    nodes.forEach((n,i)=>{
      n.classList.toggle('done',i<index);
      n.classList.toggle('active',i===index);
    });
  }

  function show(endpoint){
    const cfg=configs[endpoint], isEn=language()==='EN';
    const overlay=document.getElementById('processingOverlay');
    if(!cfg||!overlay) return;
    activeCount++;
    started=Date.now();currentStep=0;
    document.getElementById('processingTitle').textContent=(isEn?cfg.en:cfg.th)[0];
    document.getElementById('processingSub').textContent=(isEn?cfg.en:cfg.th)[1];
    renderSteps(isEn?cfg.stepsEn:cfg.stepsTh);
    document.getElementById('processingTime').textContent='0s';
    overlay.classList.remove('hidden');
    clearInterval(timer);clearInterval(clock);
    timer=setInterval(()=>{
      const total=document.querySelectorAll('.processing-step').length;
      if(total>1 && currentStep<total-1){currentStep++;markStep(currentStep)}
    },2400);
    clock=setInterval(()=>{
      const sec=Math.max(0,Math.floor((Date.now()-started)/1000));
      const el=document.getElementById('processingTime');
      if(el) el.textContent=sec+'s';
    },500);
  }

  function hide(){
    activeCount=Math.max(0,activeCount-1);
    if(activeCount>0) return;
    clearInterval(timer);clearInterval(clock);
    const nodes=[...document.querySelectorAll('.processing-step')];
    nodes.forEach(n=>{n.classList.remove('active');n.classList.add('done')});
    setTimeout(()=>document.getElementById('processingOverlay')?.classList.add('hidden'),180);
  }

  window.fetch=async function(input,init){
    const endpoint=endpointOf(input);
    if(endpoint) show(endpoint);
    try{
      return await nativeFetch(input,init);
    }finally{
      if(endpoint) hide();
    }
  };
})();
</script>
'''


def enhanced_ui() -> str:
    html = core.INDEX_HTML
    if 'id="processingOverlay"' in html:
        return html
    html = html.replace("V2.1.6 RENDER", "V2.1.7 PROCESSING")
    html = html.replace("</style>", PROCESS_CSS + "\n</style>", 1)
    html = html.replace("<body>", "<body>" + PROCESS_HTML, 1)
    html = html.replace("</body>", PROCESS_JS + "\n</body>", 1)
    return html


async def root(_: Request):
    return HTMLResponse(
        enhanced_ui(),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
        },
    )


routes = [
    Route("/", root),
    Route("/favicon.ico", core.favicon),
    Route("/healthz", core.healthz),
    Route("/api/health", core.api_health),
    Route("/api/programs", core.api_programs),
    Route("/api/ask", core.api_ask, methods=["POST"]),
    Route("/api/compare", core.api_compare, methods=["POST"]),
    Route("/api/benchmark", core.api_benchmark, methods=["POST"]),
]

app = Starlette(routes=routes, debug=False)
