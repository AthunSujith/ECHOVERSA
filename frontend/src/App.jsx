import React, { useState, useEffect } from 'react';
import './App.css';
import Home from './components/Home';
import Main from './components/Main';

function App() {
  const [view, setView] = useState('home');
  const [config, setConfig] = useState(null);

  useEffect(() => {
    // Fetch config on load to know about AI models
    fetch('http://localhost:8000/api/config')
      .then(res => res.json())
      .then(data => setConfig(data))
      .catch(err => console.error("Backend offline?", err));
  }, []);

  return (
    <div className="container">
      {view === 'home' ? (
        <Home onGetStarted={() => setView('main')} config={config} />
      ) : (
        <Main onBack={() => setView('home')} />
      )}
    </div>
  );
}

export default App;
