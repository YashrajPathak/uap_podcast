# 🎙️ UAP Podcast Generator — Multi-Agent Conversational AI Engine

**UAP Podcast** is a modular, production-grade multi-agent system built to autonomously **generate podcasts** from structured data, metrics, and context — producing **natural, human-like conversations** between specialized AI agents and synthesizing them into **high-quality audio**.

It brings together the power of **Large Language Models (LLMs)**, **Azure Speech Services**, and **conversational orchestration** to create data-driven, collaborative dialogue between domain experts.

---

## 🧠 Overview

The UAP Podcast system simulates a real-time conversation between three AI personas:

- 🤖 **Agent Nexus** – The **host and orchestrator**, setting context, introducing topics, and guiding the flow.
- 💡 **Agent Reco** – The **recommendation strategist**, advising on key metrics, insights, and strategic actions.
- 📊 **Agent Stat** – The **data integrity specialist**, validating assumptions, checking statistical robustness, and challenging conclusions.

Each agent is powered by an LLM with a **distinct system prompt**, conversational personality, and contextual understanding. Together, they produce a seamless and insightful conversation that can be directly published as a podcast.

---

## ✨ Features

✅ **Multi-Agent Conversation Flow**  
Orchestrates a structured, realistic dialogue with contextual awareness and back-and-forth dynamics.

✅ **Natural Speech Synthesis**  
Generates lifelike audio using SSML modulation, with emphasis, emotion, and prosody for each agent.

✅ **Context-Aware Recommendations**  
Processes structured data (JSON, metrics) and builds conversations around key trends, anomalies, and patterns.

✅ **End-to-End Pipeline**  
From data ingestion to final `.wav` podcast and `.txt` script — all automated.

✅ **Modular Architecture**  
Cleanly separated components for agents, models, utils, and services. Easy to extend, test, and scale.

✅ **Production-Ready API**  
FastAPI-powered backend ready for integration with web apps, dashboards, or pipeline automation.

---

## 🧱 System Architecture

The conversation pipeline is divided into **three phases**:

1. **🎬 Initialization**  
   - `NexusAgent` introduces the podcast, outlines objectives, and highlights key metrics from input data.

2. **💬 Multi-Turn Dialogue**  
   - `RecoAgent` proposes recommendations.
   - `StatAgent` validates them with statistical reasoning.
   - Conversation evolves dynamically, adapting to previous turns and data insights.

3. **🎧 Output Generation**  
   - All responses are converted to natural speech.  
   - Audio segments are stitched together into a final `.wav` file.  
   - Full transcript saved as `.txt`.

---

## 📂 Folder Structure

src/ └── uap_podcast/ ├── agents/ │   ├── nexus_agent/ │   │   ├── agent.py │   │   └── utils/ │   │       ├── nodes.py │   │       ├── state.py │   │       └── tools.py │   ├── reco_agent/ │   │   ├── agent.py │   │   └── utils/ │   │       ├── nodes.py │   │       ├── state.py │   │       └── tools.py │   └── stat_agent/ │       ├── agent.py │       └── utils/ │           ├── nodes.py │           ├── state.py │           └── tools.py │ ├── models/ │   ├── podcast.py │   └── audio.py │ ├── utils/ │   ├── config.py │   └── logging.py │ ├── tests/ │   ├── test_agents.py │   ├── test_models.py │   └── test_utils.py │ ├── server.py ├── pyproject.toml ├── README.md └── .env

---

## ⚙️ Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/your-org/uap_podcast.git
cd uap_podcast
pip install -r requirements.txt

Or with Poetry:

poetry install


---

🔑 Environment Setup

Create a .env file in the root directory:

AZURE_OPENAI_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4o
OPENAI_API_VERSION=2024-05-01-preview

TENANT_ID=your_tenant_id
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
SPEECH_REGION=eastus
RESOURCE_ID=your_resource_id


---

🚀 Running the System

🖥️ CLI Mode (Generate Podcast Offline)

python -m uap_podcast.models.podcast

You’ll be prompted to:

Choose data files (data.json, metric_data.json, or both)

Specify conversation turns

Set duration (2–5 min)


Output:

🎧 podcast_YYYYMMDD_HHMMSS.wav – Final podcast audio

📜 podcast_script_YYYYMMDD_HHMMSS.txt – Full transcript



---

🌐 API Mode (Run as a Backend Service)

Start the FastAPI server:

uvicorn uap_podcast.server:app --reload --port 8001

Available endpoints:

Endpoint	Method	Description

/generate-response	POST	Generate agent responses from system and user prompts
/generate-audio	POST	Convert text to synthesized audio
/health	GET	Health check endpoint



---

🧠 Conversation Logic

Agent Roles:

Agent	Role	Focus

Nexus	Host & Moderator	Introduce, guide, and summarize
Reco	Recommendation Specialist	Suggest metric strategies and actions
Stat	Data Integrity Expert	Validate, challenge, and provide checks



---

🔊 Speech Synthesis

We use Azure Cognitive Services with SSML for lifelike speech:

📈 Number emphasis: Key values are stressed.

❗ Emotion triggers: Words like “shocking” or “surprising” change pitch.

❓ Questions: Rising intonation.

💼 Recommendations: Calm, authoritative tone.


Example SSML snippet:

<mstts:express-as style="cheerful">
  Given that ASA dropped 84.7%, we should confirm timestamp integrity before setting a target.
</mstts:express-as>


---

✅ Quality & Safety Checks

Before finalizing any output, the system ensures:

✅ Text ≤ 50 words per response

✅ Total audio ≤ 5 minutes

✅ JSON context is parsed correctly

✅ Agent identity is validated

✅ Fallback prompts handle edge cases safely



---

🧪 Testing

Run all unit tests:

pytest tests/

Or test specific modules:

pytest tests/test_agents.py -v
pytest tests/test_models.py -v
pytest tests/test_utils.py -v


---

📍 Roadmap

[ ] 🔴 Real-time voice interaction (microphone + audio stream)

[ ] 🧠 Multi-agent memory (persistent state between episodes)

[ ] 🎤 Dynamic interruptions and live dialogue simulation

[ ] 🌐 Dashboard for monitoring conversation state and metrics

[ ] 📡 Integration with analytics pipelines for automated weekly episodes



---

🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repo


2. Create a new feature branch


3. Make changes with clear commits


4. Add/Update tests where necessary


5. Submit a pull request 🚀




---

📜 License

This project is licensed under the MIT License.
See LICENSE for more details.


---

👨‍💻 Maintainers

[Your Name] – Lead Developer

[Your Team / Org] – AI Engineering @ YourCompany



---

🌟 Acknowledgements

This project builds upon:

Azure OpenAI

Azure Cognitive Services Speech

FastAPI

LangGraph



---

> 🎙️ "Turning data into dialogue — and dialogue into decisions."
— UAP Podcast, 2025
