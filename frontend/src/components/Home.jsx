import React from 'react';

const Home = ({ onGetStarted, config }) => {
    return (
        <div className="animate-fade-in" style={{ textAlign: 'center', marginTop: '5vh' }}>
            <div className="ai-core-container">
                <div className="ai-core"></div>
            </div>

            <h1 className="delay-1">ECHOVERSA</h1>
            <p className="delay-2" style={{ fontSize: '1.5rem', marginBottom: '3rem', maxWidth: '600px', margin: '0 auto 3rem auto' }}>
                Your Advanced Local AI Companion
            </p>

            <div className="glass-card delay-3" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                    <h2 style={{ color: '#fff', margin: 0 }}>System Integrity Integrity</h2>
                    {config ? (
                        config.is_using_openai ? (
                            <span className="status-badge status-cloud">
                                <span>☁️</span> Hybrid Mode
                            </span>
                        ) : (
                            <span className="status-badge status-local">
                                <span>🛡️</span> Local Core
                            </span>
                        )
                    ) : (
                        <span className="status-badge" style={{ background: 'rgba(255,255,255,0.1)' }}>Connecting...</span>
                    )}
                </div>

                <p style={{ marginBottom: '1.5rem' }}>
                    Welcome to EchoVerse. This application is designed to provide secure, empathetic, and intelligent interactions experienced through a next-generation interface.
                </p>

                {config && config.is_using_openai ? (
                    <div style={{ padding: '1rem', borderRadius: '12px', background: 'rgba(234, 179, 8, 0.05)', border: '1px solid rgba(234, 179, 8, 0.2)', marginBottom: '2rem' }}>
                        <p style={{ fontSize: '0.9rem', margin: 0, color: '#fef08a' }}>
                            <strong>Notice:</strong> High-performance cognitive modules (OpenAI) are active. Some data processing occurs externally.
                        </p>
                    </div>
                ) : (
                    <div style={{ padding: '1rem', borderRadius: '12px', background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)', marginBottom: '2rem' }}>
                        <p style={{ fontSize: '0.9rem', margin: 0, color: '#bae6fd' }}>
                            <strong>Secure:</strong> All processing is handled by the Local AI Core. Your data remains completely private.
                        </p>
                    </div>
                )}

                <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                    <button className="btn-primary" onClick={onGetStarted}>
                        Initialize Session <span>→</span>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Home;
