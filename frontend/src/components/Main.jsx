import React, { useState } from 'react';

const Main = ({ onBack }) => {
    const [input, setInput] = useState('');
    const [response, setResponse] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        setLoading(true);
        setError(null);
        setResponse(null);

        try {
            const res = await fetch('http://localhost:8000/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: input, inputType: 'text' })
            });

            if (!res.ok) throw new Error("Failed to generate response");

            const data = await res.json();
            setResponse(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-fade-in" style={{ width: '100%', maxWidth: '800px', margin: '0 auto' }}>
            <button
                onClick={onBack}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', marginBottom: '1rem', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
                <span>←</span> Back to Home
            </button>

            <div className="glass-card">
                <h2 style={{ color: '#fff' }}>How are you feeling today?</h2>
                <form onSubmit={handleSubmit}>
                    <textarea
                        className="input-field"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Share your thoughts..."
                        rows={4}
                        style={{ resize: 'vertical' }}
                    />
                    <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? 'Processing...' : 'Send Message'}
                    </button>
                </form>
            </div>

            {error && (
                <div style={{ marginTop: '2rem', color: '#ef4444', textAlign: 'center' }}>
                    Error: {error}
                </div>
            )}

            {response && (
                <div className="animate-fade-in" style={{ marginTop: '2rem' }}>
                    <div className="glass-card" style={{ marginBottom: '2rem', borderLeft: '4px solid #38bdf8' }}>
                        <h3 style={{ color: '#38bdf8', marginTop: 0 }}>Supportive Response</h3>
                        <p style={{ color: '#f8fafc', whiteSpace: 'pre-wrap' }}>{response.supportive_statement}</p>
                    </div>

                    <div className="glass-card" style={{ borderLeft: '4px solid #818cf8', fontStyle: 'italic' }}>
                        <h3 style={{ color: '#818cf8', marginTop: 0 }}>A Poem for You</h3>
                        <p style={{ whiteSpace: 'pre-line', color: '#e2e8f0', lineHeight: '1.8' }}>{response.poem}</p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Main;
