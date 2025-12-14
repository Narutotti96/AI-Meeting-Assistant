# 🎯 AI Meeting Assistant

> Real-time transcription and AI-powered suggestions for video conferences

An intelligent assistant that listens to your video meetings (Teams, Zoom, Google Meet), transcribes conversations in real-time, and provides AI-powered suggestions using DeepSeek AI.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)

## ✨ Features

- 🎤 **Real-time Audio Capture** - Captures system audio from video conferencing apps
- 📝 **Live Transcription** - Uses Whisper AI for accurate speech-to-text
- 🤖 **AI Suggestions** - DeepSeek AI analyzes conversations and provides contextual suggestions
- ⌨️ **Global Hotkeys** - Control the assistant even when the terminal is minimized
- 🪟 **Desktop Notifications** - Large, readable Zenity notifications with suggestions
- 💾 **Automatic Logging** - All transcriptions saved with timestamps
- 🌍 **Multi-language** - Supports Italian, English, and other languages

## 🎬 Demo

```
🎙️  IN ASCOLTO...
💬 [IT] (2.3s): "Dobbiamo discutere il budget per il prossimo trimestre"
💬 [IT] (1.8s): "Quali sono le priorità principali?"

[Press Ctrl+Alt+S]
💡 SUGGERIMENTI AI:
1. Proporre una riunione di follow-up per dettagli
2. Chiedere feedback sul budget proposto
3. Condividere documentazione via email
```

## 🚀 Quick Start

### Prerequisites

- Ubuntu 22.04+ (or Debian-based Linux)
- Python 3.10+
- DeepSeek API Key ([Get one here](https://platform.deepseek.com))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Narutotti96/AI-Meeting-Assistant.git
cd AI-Meeting-Assistant

# 2. Install system dependencies
sudo apt update
sudo apt install zenity portaudio19-dev python3-dev

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Configure API key
export DEEPSEEK_API_KEY='your-api-key-here'
# Or create a .env file:
echo 'DEEPSEEK_API_KEY="your-api-key"' > .env

# 6. List audio devices
python Main.py --list-devices

# 7. Run the assistant
python Main.py --audio-device YOUR_DEVICE_ID
```

## ⌨️ Global Hotkeys

| Hotkey | Action |
|--------|--------|
|`  Press  S  `| 💡 Request AI suggestions |
| `Ctrl+Alt+R` | 📋 Generate meeting summary |
| `Ctrl+Alt+C` | 🗑️ Clear conversation history |
|`  Press  Q  `| 👋 Exit the assistant |

## 📖 Usage

### Basic Usage

```bash
python Main.py --audio-device 14
```

### Advanced Options

```bash
# Use a different Whisper model
python Main.py --model small --audio-device 14

# Change language
python Main.py --language en --audio-device 14

# Use GPU (if available)
python Main.py --device cuda --audio-device 14

# Debug mode
python Main.py --debug --audio-device 14
```

## 🎛️ Configuration

### Audio Device Setup (Ubuntu)

The assistant needs to capture your system's audio output (what you hear in meetings).

```bash
# 1. Find your audio monitor device
pactl list sources short | grep monitor

# Example output:
# 111  alsa_output.pci-0000_00_1f.3.analog-stereo.monitor

# 2. Use the device ID from --list-devices that matches
python Main.py --list-devices
```

### DeepSeek API Key

Get your free API key from [DeepSeek Platform](https://platform.deepseek.com).

```bash
# Method 1: Environment variable
export DEEPSEEK_API_KEY='sk-...'

# Method 2: .env file (recommended)
echo 'DEEPSEEK_API_KEY="sk-..."' > .env
```

## 📁 Project Structure

```
AI-Meeting-Assistant/
├── Main.py                 # Entry point
├── pipeline.py             # Core assistant logic
├── Audio.py                # Audio capture module
├── ImprovedNotifier.py     # Notification system
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🔧 Troubleshooting

### "No audio device found"

```bash
# Enable audio loopback
pactl load-module module-loopback

# Check if PipeWire is running
systemctl --user status pipewire
```

### "ModuleNotFoundError: No module named 'gi'"

System tray is optional. Run without it:
```bash
python Main.py --audio-device 14
# (System tray is automatically disabled if GTK not available)
```

### "API Key not configured"

Make sure you've set the environment variable or created a `.env` file:
```bash
export DEEPSEEK_API_KEY='your-key'
```

### Notifications not appearing

```bash
# Install Zenity
sudo apt install zenity

# Test notification
zenity --info --text="Test" --timeout=5
```

## 🛠️ Development

### Requirements

- Python 3.10+
- faster-whisper
- DeepSeek API access
- PulseAudio/PipeWire

### Running Tests

```bash
# Test audio capture
python Audio.py

# Test notifications
python ImprovedNotifier.py

# Test with debug output
python Main.py --debug --audio-device 14
```

## 📝 Transcription Logs

All transcriptions are automatically saved to `conversazione_log.txt`:

```
[2024-12-15 14:30:25] Dobbiamo discutere il budget
[2024-12-15 14:30:32] Quali sono le priorità?
[2024-12-15 14:30:45] Possiamo organizzare un follow-up
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Whisper](https://github.com/openai/whisper) - Speech recognition by OpenAI
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Faster Whisper implementation
- [DeepSeek](https://platform.deepseek.com) - AI language model
- [pynput](https://github.com/moses-palmer/pynput) - Global hotkeys

## ⚠️ Disclaimer

This tool is for personal productivity enhancement. Always:
- ✅ Inform meeting participants you're using an AI assistant
- ✅ Respect privacy laws in your jurisdiction
- ✅ Check your company's policy on recording/AI tools
- ✅ Use responsibly and ethically

## 📧 Contact

For questions or suggestions, please open an issue on GitHub.

---

**Made with ❤️ for productive meetings**
