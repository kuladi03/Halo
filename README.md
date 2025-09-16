# 🤖 Halo Assistant

Halo is a **personal real-time AI assistant** designed for meetings, coding, and technical discussions.  
It listens, transcribes, understands context, and responds instantly — like your own private copilot that runs **locally and offline**.


## ✨ Features
- 🎙️ **Real-time Speech-to-Text (STT)** with [Whisper](https://github.com/openai/whisper)  
- 🤖 **AI Reasoning** using [Ollama](https://ollama.ai/) with free open-source LLMs (Mistral, LLaMA, Mixtral, etc.)  
- 🗣️ **Text-to-Speech (TTS)** option for spoken replies  
- 🖥️ **Floating Overlay UI** for quick access (Cluely-style window)  
- 🔌 **Multiple Modes**  
  - Meeting assistant  
  - Interview prep  
  - Coding assistant  
  - Custom workflows  
- 📂 **Automatic transcripts & logs** stored locally  
- ⚡ **GPU acceleration** with NVIDIA CUDA (for fast Whisper + LLM inference)  
- 🔒 100% **private & offline** (no external API calls required)


## 📂 Project Structure
```

halo-assistant/
│── README.md
│── requirements.txt
│── setup.py
│── .env
│── main.py
│
├── configs/          # Settings for models, UI, etc.
├── data/             # Transcripts, logs, cache
├── halo/
│   ├── ui/           # Overlay, controls, themes
│   ├── core/         # Listener, STT, LLM, TTS, pipeline
│   ├── utils/        # Helpers (logging, hotkeys, file utils)
│   └── modes/        # Meeting, interview, coding modes
└── tests/            # Unit tests

```

## 🛠️ Installation

### 1. Clone Repo
```
git clone https://github.com/<your-username>/halo-assistant.git
cd halo-assistant
````

### 2. Create Conda Env

```
conda create -n halo python=3.10 -y
conda activate halo
```

### 3. Install Dependencies

```
pip install -r requirements.txt
```

### 4. Install Ollama (for LLMs)

Follow instructions here: [Ollama Install](https://ollama.ai/download)

Example: Run **Mistral**

```
ollama run mistral
```

## 🚀 Usage

### Run the assistant

```bash
python main.py
```

### Start UI (Streamlit prototype)

```bash
streamlit run halo/ui/overlay.py
```

### Example Workflow

1. Start Halo
2. It listens to your mic and detects when someone speaks
3. Speech → Text (Whisper)
4. Text → Reasoning (Ollama model)
5. AI generates a smart reply
6. (Optional) Reply spoken aloud with TTS


## 🧠 Models

* **Speech-to-Text (STT)**

  * Whisper (`tiny`, `base`, `small`, `medium`, `large`)
* **Large Language Models (LLMs)**

  * Free alternatives via **Ollama**:

    * [Mistral](https://mistral.ai)
    * [LLaMA 2](https://ai.meta.com/llama/)
    * [Mixtral](https://mistral.ai/news/mixtral/)
  * Easily switchable in `configs/settings.yaml`

## 🗺️ Roadmap

* [ ] Real-time voice activity detection (VAD)
* [ ] Always-on floating overlay
* [ ] Multi-language transcription
* [ ] Context memory across sessions
* [ ] Desktop app build (PyQt / Electron)



## 🤝 Contributing

Contributions, feature requests, and bug reports are welcome!
Please fork the repo, open an issue, or submit a pull request.

---
Built with ❤️ for personal productivity.

