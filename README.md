# 🎵 EchoVerse Companion Application

A local-first AI companion that provides personalized emotional support through multi-modal input processing, AI-generated content, and audio processing.

## ✨ Features

- 🔒 **Privacy First**: All data stays on your device
- 💬 **Multi-Modal Input**: Text, audio, and drawings
- 🤖 **AI Support**: Personalized responses and poems
- 🎵 **Audio Generation**: Text-to-speech with music remixing
- 📚 **History Tracking**: Track your emotional journey
- 🛡️ **Defensive Design**: Works even when services are unavailable

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
streamlit run app/streamlit_workspace.py
```

### 3. Open in Browser
Navigate to: http://localhost:8501

## 🎯 How to Use

1. **Create Account**: Sign up with a nickname and password
2. **Input Content**: Type text, upload audio, or draw
3. **Get Support**: Receive AI-generated supportive responses and poems
4. **Listen**: Convert text to speech with optional music
5. **Track History**: Review your interactions over time

## 🔧 Optional Enhancements

For the full experience, install optional dependencies:

```bash
# Enhanced AI (better than local models)
pip install google-generativeai

# Better audio processing
pip install pyttsx3 pydub openai-whisper

# Drawing input support
pip install streamlit-drawable-canvas
```

Add API keys for premium features:
```bash
export GOOGLE_API_KEY="your_gemini_api_key"
export ELEVENLABS_API_KEY="your_elevenlabs_api_key"
```

## 📁 Project Structure

```
echoverse-companion-app/
├── app/                    # Core application modules
├── Test/                   # Comprehensive test suite
├── users/                  # User data (created automatically)
├── logs/                   # Application logs
├── download/               # AI model downloads
└── Documentation files     # Project documentation
```

## 🛠️ System Requirements

- **Minimum**: Python 3.8+, 4GB RAM, 2GB disk space
- **Recommended**: Python 3.10+, 8GB RAM, 10GB disk space
- **For Local AI**: 16GB+ RAM, GPU optional but recommended

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're in the project directory and dependencies are installed
2. **Port Already in Use**: Change port with `--server.port 8502`
3. **Missing Features**: Install optional dependencies for full functionality

### Debug Mode
Click the 🔧 button in the app to see system status and performance metrics.

## 📊 What's Working

The app runs successfully with graceful fallbacks:
- ✅ Core functionality (text input, user accounts, history)
- ✅ Local AI models (TinyLlama for content generation)
- ✅ Mock generators (always available as fallback)
- ✅ Basic audio processing (without premium features)
- ✅ Comprehensive error handling and logging

## 🎉 Ready to Use!

The application is fully functional right now. Optional enhancements will unlock additional features, but the core emotional support experience is complete and ready to help users on their journey.

---

**Status**: ✅ Partial Production Ready  
**Last Updated**: December 2024  
