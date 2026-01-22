# Lyria Studio V2: Hybrid Audio Architecture

## Overview
This repository hosts the V2 architecture for the Athena Audio Engine. It transitions from a monolithic script to a Client-Server architecture, decoupling the generation logic (Python/FastAPI) from the user experience (React/Next.js).

This hybrid approach allows for a "Consumer-Grade" chat interface for rapid ideation, while retaining a "Pro-Grade" studio environment for granular DSP editing.

DEMO: https://youtu.be/lGW3Mi-l6m0

---

## Quick Start (Execution Guide)
### QUICK ACCESS LINK (Live Version)
The public partial/client UI (No advanced settings) is deployed on Vercel and accessible here:
**https://lyria-studio.vercel.app/**

# Local
To run the full suite, you need 3 separate terminals running concurrently.

### Terminal 1: The Backend Core (API)
Handles the connection to Vertex AI and exposes the generation endpoints.

cd backend
# Ensure your environment is active (e.g., conda activate stitch_test)
uvicorn api:app --reload --port 8000

### Terminal 2: The Frontend Client (UI)
Launches the Next.js Chat Interface (Consumer View).

cd frontend
npm run dev
# Running on http://localhost:3000

### Terminal 3: The Advanced Studio (DSP Engine)
Launches the Deep Editor for segmentation and stitching.

cd backend
streamlit run studio.py --server.port 8501

**Usage Flow:**
1. Open http://localhost:3000
2. Generate a track using the Chat UI.
3. Click "Open in Studio" to transfer the asset to the advanced editor.

---

## Installation & Setup

### Prerequisites
* Python 3.10+ (Recommended: Anaconda/Miniconda)
* Node.js 18+ (LTS Version)
* **FFmpeg** installed and added to system PATH
  * macOS: `brew install ffmpeg`
  * Linux: `sudo apt-get install ffmpeg`
  * Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### 1. Backend Setup
Initialize the Python environment for signal processing and API management.

cd backend
pip install -r requirements.txt

**Environment Variables Required:**
- `PROJECT_ID`: Your Google Cloud Project ID
- `LOCATION`: Vertex AI region (default: `us-central1`)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your service account JSON key file
- `GOOGLE_API_KEY`: Your Google AI Studio API key for Gemini 1.5 Pro (for video-to-music feature)

Example `.env` file:
```
PROJECT_ID=your-gcp-project-id
LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_API_KEY=your-gemini-api-key
```

**Note:** The backend now uses Vertex AI SDK with service account authentication. Ensure your service account has the necessary permissions to access the Lyria-002 model. For the video-to-music feature, you'll also need a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

### 2. Frontend Setup
Install the React dependencies and UI component libraries.

cd frontend
npm install

---

## Features

### 1. Text-to-Music Generation
Generate high-fidelity music from text prompts using Google's Lyria 2 model.
- Enter a descriptive prompt (e.g., "Upbeat synthwave track with heavy bass")
- Optional negative prompts and seed values for reproducibility
- 30-second, 48kHz stereo audio output

### 2. Video-to-Music Workflow (NEW)
Automatically generate and add music to your videos using AI:

**How it works:**
1. **Upload Video**: Click the video icon and select an MP4/MOV file (max 100MB)
2. **AI Analysis**: Gemini 1.5 Pro analyzes the video's mood, pacing, and energy
3. **Music Generation**: Lyria 2 creates a custom soundtrack based on the analysis
4. **Auto-Merge**: FFmpeg combines the generated music with your video
5. **Download**: Get your video with the AI-generated soundtrack

**Supported formats:** MP4, MOV, AVI, MKV

### 3. Advanced Studio Editor
Fine-tune your generated tracks with the Streamlit-based studio:
- Segment audio into sections
- Regenerate specific segments with new prompts
- Smart crossfade stitching
- Export final masters

---

## System Architecture & File Roles

### Backend Layer (/backend)
Contains the proprietary logic for audio manipulation and external model orchestration.

* api.py
    * Role: REST Interface & Entry Point.
    * Function: Handles CORS policies and routes JSON requests from the Frontend to the generation engine. Exposes specific headers for cross-origin file handling.
* studio.py
    * Role: Advanced DSP Visualizer.
    * Function: A specialized environment for non-linear editing. Handles the "Session State" when importing assets from the chat and executes the final rendering pipeline.
* audio_utils.py
    * Role: Signal Processing Middleware.
    * Function: Contains the core algorithms for "Smart Stitching," crossfade calculation, and temporary file management. This is the DSP engine of the project.
* lyria_generator.py
    * Role: Model Gateway.
    * Function: Manages the Vertex AI REST API connection to the Google Lyria-002 model, handling batch generation and audio file output.
* gemini_vibe_agent.py
    * Role: Video Analysis Agent.
    * Function: Uses Gemini 1.5 Pro multimodal capabilities to analyze videos and generate optimized music prompts for Lyria 2.
* video_processor.py
    * Role: Video Processing Engine.
    * Function: FFmpeg wrapper for merging audio with video, validating video files, and extracting video metadata.

### Frontend Layer (/frontend)
A modern, responsive client built with Next.js 14 (App Router).

* src/app/page.tsx
    * Role: Client State Manager.
    * Function: Manages the chat history, audio playback states, and the logic that constructs the deep links to open the Studio with the correct context.
* src/app/layout.tsx
    * Role: Global Context.
    * Function: Handles font optimization and suppresses hydration warnings for browser extensions compatibility.

---

## Notes for Deployment
* Storage: Currently uses local ephemeral storage for low-latency processing during the MVP phase. Production migration would require an S3/GCS bucket implementation.
* Security: The API currently allows all origins for development ease. This must be restricted to the specific frontend domain in production.
EOF
