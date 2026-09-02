import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import type { AnswerResult, BenchmarkResult, HealthResult, NavigationTab } from './types';

const tabs: [NavigationTab, string][] = [
  ['dashboard', 'ถาม-ตอบ'],
  ['comparison', 'เปรียบเทียบ'],
  ['benchmarks', 'Benchmark'],
  ['reliability', 'Reliability'],
];

function App() {
  const [tab, setTab] = useState<NavigationTab>('dashboard');
  const [question, setQuestion] = useState('AIT เรียนกี่หน่วยกิต และกี่ปี?');
  const [answer, setAnswer] = useState<AnswerResult | null>(null);
  const [health, setHealth] = useState<HealthResult | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function post(path: string, body: unknown) {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }

  async function ask() {
    setLoading(true);
    try {
      setAnswer(await post('/api/ask', { question }));
    } catch (e) {
      setAnswer({
        status: 'ERROR',
        answer: String(e),
        programs: [],
        latency_ms: 0,
        cache_hit: false,
        verification: null,
        evidence: [],
      });
    } finally {
      setLoading(false);
    }
  }

  async function runBenchmark() {
    setBenchmark(await post('/api/benchmark', {}));
  }

  useEffect(() => {
    fetch('/api/health').then(r => r.json()).then(setHealth).catch(() => null);
  }, []);

  return (
    <main className="app">
      <header className="hero">
        <h1>ThaiLLM <span>Academic Intelligence</span></h1>
        <p>WWWW UI + ThaiLLM Evidence Grounded Competition System</p>
        <nav>{tabs.map(([id, label]) => <button className={tab === id ? 'active' : ''} onClick={() => setTab(id)} key={id}>{label}</button>)}</nav>
      </header>

      {tab === 'dashboard' && <section className="card">
        <textarea value={question} onChange={e => setQuestion(e.target.value)} />
        <button onClick={ask}>{loading ? 'กำลังวิเคราะห์...' : 'ถาม ThaiLLM'}</button>
        {answer && <Result data={answer} />}
      </section>}

      {tab === 'comparison' && <section className="card">
        <h2>Compare</h2>
        <button onClick={() => post('/api/compare', { left: 'AIT', right: 'DSBA', focus: 'รายวิชาและทักษะ' }).then(setAnswer)}>AIT vs DSBA</button>
        {answer && <Result data={answer} />}
      </section>}

      {tab === 'benchmarks' && <section className="card">
        <button onClick={runBenchmark}>Run Benchmark</button>
        {benchmark && <pre>{JSON.stringify(benchmark, null, 2)}</pre>}
      </section>}

      {tab === 'reliability' && <section className="card">
        <h2>System Health</h2>
        <pre>{JSON.stringify(health, null, 2)}</pre>
      </section>}
    </main>
  );
}

function Result({ data }: { data: AnswerResult }) {
  return <div className="result">
    <h2>{data.status}</h2>
    <p>{data.answer}</p>
    <h3>Evidence</h3>
    {data.evidence.map((e, i) => <article key={i}><b>{e.source}</b> หน้า {e.page}<br />{e.text}</article>)}
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
