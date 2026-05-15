# AURA — AI Caregiving Assistant

**AURA** is a personal AI-powered caregiving assistant designed to support an elderly person in everyday life.

The project combines a conversational AI assistant, medication reminders, emergency notifications, speech output, doctor-mode communication, translation support, Telegram alerts and a mobile-friendly control interface.

It was built as a practical health-tech prototype focused on accessibility, family caregiving, real-world deployment and multimodal interaction.

> Privacy note: the public version of this repository should not contain real patient data, medical records, API keys, bot tokens or private chat identifiers.

---

## Overview

AURA was created to solve a real caregiving problem: helping an elderly person interact with technology, remember important actions, communicate health-related information and quickly contact a family member when needed.

The system is designed around three main users:

- the patient;
- the caregiver / family member;
- the doctor or medical professional.

AURA can speak in a warm, simple and human-like tone, while also providing a separate doctor-oriented mode with more structured medical context.

---

## Key Features

### AI Assistant

AURA includes an AI assistant powered by OpenAI.

The assistant can:

- answer everyday questions;
- provide calm conversational support;
- use predefined patient context;
- remember recent chat history;
- adapt tone for elderly users;
- switch between normal mode and doctor mode;
- send important alerts to a caregiver through Telegram.

The assistant logic is separated into a dedicated AI module, which keeps the main backend cleaner and easier to maintain.

---

### Normal Mode and Doctor Mode

AURA supports two interaction modes:

#### Normal Mode

Designed for everyday conversation with the patient.

The assistant uses:

- short responses;
- warm tone;
- simple wording;
- emotionally supportive phrasing;
- minimal technical complexity.

#### Doctor Mode

Designed for situations where a doctor or medical professional needs a structured summary.

This mode can provide:

- medical context;
- medication-related information;
- symptom summaries;
- caregiver notes;
- more formal and structured explanations.

This separation demonstrates prompt engineering for different user roles and contexts.

---

### Medication Reminders

AURA includes a reminder system for medication schedules.

The backend can:

- return the current medication schedule;
- enable reminders;
- disable reminders;
- store reminder state;
- trigger local voice reminders;
- avoid repeatedly firing the same reminder.

This functionality is implemented as part of the FastAPI backend and is designed to run continuously on a local device.

---

### Speech Output

AURA supports voice output.

The system uses:

- OpenAI Text-to-Speech API;
- long text splitting for TTS;
- retry logic;
- local audio playback through Termux;
- fallback to Termux TTS when OpenAI TTS fails.

This makes the assistant more accessible for users who may have difficulty reading from a screen.

---

### SOS and Telegram Alerts

The project includes emergency-style communication features.

AURA can send Telegram notifications to a caregiver when:

- the user presses an SOS button;
- the user provides additional SOS details;
- the assistant detects that a caregiver should be informed;
- geolocation data is available.

Telegram integration is used as a lightweight and reliable notification channel.

---

### Geolocation Tracking

A separate geolocation module can send the device location to Telegram.

It uses Termux location providers:

- network location;
- GPS fallback;
- error reporting to Telegram;
- scheduled location checks.

This is intended for safety scenarios where a caregiver needs to know the user’s location.

---

### Translator Mode

AURA includes a translator mode for communication between the patient and a doctor.

The translator flow supports:

- starting translation mode;
- stopping translation mode;
- translating user messages;
- assisting in multilingual medical communication.

This is especially useful when the patient does not speak the local language.

---

### Billing / Usage Monitoring

The backend includes an endpoint for checking OpenAI usage and estimated balance.

This helps keep API costs under control when the assistant runs continuously.

---

### Frontend Interface

The frontend is built with:

- Next.js;
- React;
- TypeScript;
- Tailwind CSS;
- lucide-react.

It provides a mobile-friendly UI for interacting with the assistant and controlling core features.

---

### Android / Termux Deployment

AURA is designed to run on an Android device through Termux.

The startup script handles:

- wake lock;
- environment variables;
- dependency installation;
- Python package installation;
- Termux API setup;
- autostart configuration through Termux:Boot;
- backend launch.

This makes the project more than a web prototype: it is designed for real device deployment.

---

## Tech Stack

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- Requests
- python-dotenv
- TheFuzz
- Transliterate
- DuckDuckGo Search

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- lucide-react

### AI and Speech

- OpenAI Chat API
- OpenAI Text-to-Speech API
- Termux TTS fallback
- Local audio playback

### Integrations

- Telegram Bot API
- Termux API
- Termux Location
- Termux:Boot

### Deployment Target

- Android device
- Termux environment
- Local network frontend/backend usage

---

## Project Structure

```text
Project-Aura/
├── backend/
│   ├── main.py              # FastAPI backend and API routes
│   ├── ai_assistant.py      # OpenAI assistant, prompts, modes, history
│   ├── geo_tracker.py       # Location tracking and Telegram reporting
│   ├── requirements.txt     # Python dependencies
│   └── start_aura.sh        # Android / Termux startup script
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Main UI
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   └── eslint.config.mjs
│
└── README.md
```

---

## API Overview

The backend exposes several groups of endpoints.

### Health and Status

```text
GET /
```

Used to check whether the backend is running.

### AI Chat

```text
POST /ai-chat
POST /ai-chat/doctor-mode
POST /ai-chat/normal-mode
GET  /ai-chat/history
POST /ai-chat/clear
```

Used for AI conversations, mode switching and chat history management.

### Medication Reminders

```text
GET  /get-meds-schedule
POST /enable-reminders
POST /disable-reminders
```

Used to manage medication reminders.

### SOS

```text
POST /sos/alert
POST /sos/details
```

Used to send emergency alerts and additional details to the caregiver.

### Translator

```text
POST /translator/start
POST /translator/stop
POST /translator/translate
```

Used for patient-doctor translation workflows.

### Billing

```text
GET /billing/balance
```

Used to monitor OpenAI usage and estimated remaining budget.

### Media

```text
GET /search-movie
GET /video-stream
```

Used for local media search and playback functionality.

---

## Running Locally

### Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

On Windows:

```bat
cd backend

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

The backend runs on:

```text
http://localhost:8000
```

---

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on:

```text
http://localhost:3000
```

---

## Environment Variables

AURA should be configured through environment variables.

Example:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_ADMIN_KEY=your_openai_admin_key_optional
AURA_BOT_TOKEN=your_telegram_bot_token
AURA_SON_CHAT_ID=your_telegram_chat_id
OPENAI_CREDIT_TOTAL=5.00
```

For public repositories, create an `.env.example` file instead of committing real secrets.

---

## Android / Termux Setup

Install required packages in Termux:

```bash
pkg update -y
pkg upgrade -y

pkg install -y python rust binutils
pkg install -y libxml2 libxslt
pkg install -y termux-api
pkg install -y git
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Run AURA:

```bash
bash start_aura.sh
```

For automatic startup after reboot, the project uses Termux:Boot.

---

## Architecture

AURA follows a modular architecture:

```text
Frontend UI
   ↓
FastAPI backend
   ↓
AI assistant module
   ↓
OpenAI / Telegram / Termux integrations
```

The backend acts as the central coordinator between:

- the web interface;
- AI responses;
- speech output;
- reminder scheduling;
- emergency notifications;
- translation mode;
- geolocation;
- local device capabilities.

This architecture allows the project to run locally while still integrating cloud AI services.

---

## Engineering Decisions

### Why FastAPI?

FastAPI provides a simple and efficient way to expose local APIs for the frontend while keeping the backend easy to extend.

It is suitable for:

- JSON APIs;
- async-friendly workflows;
- integration with external services;
- background reminder logic;
- local device automation.

---

### Why Termux?

Termux allows an Android device to act as a lightweight local server.

This makes it possible to use:

- local audio playback;
- TTS fallback;
- geolocation;
- wake locks;
- autostart;
- continuous background operation.

This is important because AURA is designed for practical caregiving scenarios, not only as a desktop demo.

---

### Why Telegram?

Telegram provides a reliable and simple notification channel.

It allows the caregiver to receive:

- SOS alerts;
- location updates;
- important assistant messages;
- system error notifications.

This avoids building a custom mobile notification backend at the prototype stage.

---

### Why Prompt Modes?

The assistant has different communication requirements depending on the situation.

A patient-facing assistant should be calm, warm and simple.

A doctor-facing assistant should be structured, factual and concise.

Separating these modes improves usability and demonstrates role-based prompt design.

---

## What This Project Demonstrates

This project demonstrates practical experience with:

- building AI-assisted applications;
- integrating OpenAI into a real product workflow;
- prompt engineering for different user roles;
- FastAPI backend development;
- Next.js frontend development;
- Telegram Bot API integration;
- Android automation through Termux;
- text-to-speech implementation;
- emergency notification flows;
- local persistence and state management;
- health-tech UX thinking;
- privacy-aware software design;
- deploying software for a real-world non-technical user.

---

## Privacy and Security

This type of project requires extra care.

Before publishing or sharing the repository:

- remove all real patient data;
- remove names, addresses, dates of birth and medical records;
- remove all API keys and Telegram tokens;
- rotate any secrets that were previously committed;
- move secrets to environment variables;
- add `.env` to `.gitignore`;
- restrict CORS for production use;
- add authentication before exposing the backend;
- avoid storing sensitive medical data in plain text;
- document that the assistant is not a medical device.

Recommended `.gitignore` additions:

```gitignore
.env
.env.local
*.log
chat_history.json
state.json
last_fired.json
aura_tts.mp3
__pycache__/
*.pyc
.DS_Store
.vscode/
.idea/
.claude/
```

---

## Medical Disclaimer

AURA is a caregiving support tool and prototype.

It does not:

- diagnose diseases;
- prescribe medication;
- replace doctors;
- replace emergency services;
- guarantee medical accuracy.

In urgent situations, users should contact medical professionals or emergency services.

---

## Future Improvements

Possible next steps:

- authentication for caregiver access;
- encrypted storage of patient context;
- protected admin panel;
- medication confirmation flow;
- caregiver dashboard;
- multi-contact emergency escalation;
- structured medical report export;
- Docker-based deployment;
- unit and integration tests;
- frontend E2E tests;
- cloud sync for logs and reminders;
- configurable prompt profiles;
- safer secret management;
- role-based access control.

---

## Status

AURA is a functional prototype built for a real caregiving use case.

The project focuses on practical integration of AI, voice, reminders, emergency communication and mobile deployment in a single assistant system.

---

## Author

Created by **Vladimir Zadorozhnyi** as a portfolio project demonstrating AI product development, FastAPI backend architecture, Next.js frontend work, Telegram integration, Android automation through Termux and practical health-tech problem solving.