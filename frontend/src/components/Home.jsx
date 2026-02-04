import React from 'react';

const Home = ({ onGetStarted, config }) => {
    return (
        <div className="animate-fade-in" style={{ textAlign: 'center', marginTop: '10vh' }}>
            <h1>ECHOVERSA</h1>
            <p style={{ fontSize: '1.5rem', marginBottom: '3rem' }}>
                Your Advanced Local AI Companion
            </p>

            <div className="glass-card" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'left' }}>
                <h2 style={{ color: '#fff', marginBottom: '1rem' }}>System Integrity & AI Source</h2>

                <p>
                    Welcome to EchoVersa. This application is designed to provide secure, empathetic, and intelligent interactions.
                </p>

                {config && config.is_using_openai ? (
                    <div style={{ padding: '1rem', background: 'rgba(234, 179, 8, 0.1)', borderLeft: '4px solid #eab308', margin: '1rem 0' }}>
                        <h3 style={{ color: '#eab308', margin: 0 }}>⚠️ OpenAI / External Sources Detected</h3>
                        <p style={{ fontSize: '0.9rem' }}>
                            This system authenticates and utilizes OpenAI public APIs for enhanced cognitive processing.
                            Please be aware that data processed through these specific modules leaves the local environment.
                            All other modules remain strictly local.
                        </p>
                    </div>
                ) : (
                    <div style={{ padding: '1rem', background: 'rgba(56, 189, 248, 0.1)', borderLeft: '4px solid #38bdf8', margin: '1rem 0' }}>
                        <h3 style={{ color: '#38bdf8', margin: 0 }}>🛡️ Local AI Core Active</h3>
                        <p style={{ fontSize: '0.9rem' }}>
                            All public API requirements are currently fulfilled by our <strong>Local AI</strong> engine.
                            No external providers are utilized for your core interactions, ensuring maximum privacy and data sovereignty.
                        </p>
                    </div>
                )}

                <p>
                    Experience the future of personal companionship with our fully functional emotional support system.
                </p>

                <div style={{ textAlign: 'center', marginTop: '2rem' }}>
                    <button className="btn-primary" onClick={onGetStarted}>
                        Get Started
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Home;
