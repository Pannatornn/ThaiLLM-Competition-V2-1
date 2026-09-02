import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

function App(){
  const [q,setQ]=useState('');
  const [answer,setAnswer]=useState<any>(null);
  const [loading,setLoading]=useState(false);

  async function ask(){
    if(!q.trim()) return;
    setLoading(true);
    try{
      const r=await fetch('/api/ask',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({question:q})
      });
      setAnswer(await r.json());
    }catch(e){
      setAnswer({status:'ERROR',answer:String(e)});
    }finally{
      setLoading(false);
    }
  }

  return <main className="app">
    <header>
      <h1>ThaiLLM <span>Academic Intelligence</span></h1>
      <p>WWWW UI + ThaiLLM Evidence Grounded System</p>
    </header>

    <section className="card">
      <textarea value={q} onChange={e=>setQ(e.target.value)} placeholder="ถามเกี่ยวกับหลักสูตร AIT / DSBA / IT / IT Inter" />
      <button onClick={ask}>{loading?'กำลังวิเคราะห์...':'ถาม ThaiLLM'}</button>
    </section>

    {answer && <section className="card result">
      <h2>{answer.status}</h2>
      <pre>{answer.answer}</pre>
      <h3>Evidence</h3>
      {(answer.evidence||[]).map((e:any,i:number)=><div key={i} className="evidence">
        {e.source} หน้า {e.page}<br/>{e.text}
      </div>)}
    </section>}
  </main>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
