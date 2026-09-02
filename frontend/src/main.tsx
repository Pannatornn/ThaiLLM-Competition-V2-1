import React from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App(){
  return <main className="app"><h1>ThaiLLM Academic Intelligence</h1><p>WWWW UI integration connected to ThaiLLM backend.</p></main>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
