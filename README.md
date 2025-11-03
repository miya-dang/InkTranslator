# Ink Translator - Manga/Webcomic Translation API

Full-stack multilingual manga/webcomic translation tool that includes:

- A backend API for automatic manga translation using Optical Character Recognition, Machine Translation API, and Image Inpainting.

- This API powers a frontend app that allows users to upload manga pages and receive translated images — with the translated text rendered directly into the source panels.

# Features

OCR text extraction with Manga-OCR and EasyOCR

Translation with Google Translate and DeepL API

Image inpainting and text rendering

Supported languages: English, Japanese, Korean, Chinese, and Vietnamese

User authentication and project storage via Supabase

# Installation & Setup

### Prerequisites

Python ≥ 3.13

Node.js ≥ 18.0

Git

A Supabase account (for auth + DB)

A DeepL Translate API key

### 1️⃣ Clone the Repository
git clone https://github.com/miya-dang/InkTranslator.git
cd InkTranslator/backend

### 2️⃣ Backend Setup (FastAPI)

**Create Virtual Environment & Install Dependencies**
cd backend
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows

pip install -e .

If you don’t use editable installs, you can instead run:

pip install -r requirements.txt

**🔐 Environment Variables**

Create a .env file inside backend/src like this:

APP_NAME=Ink Translator API
APP_VERSION=0.0.0
APP_DESCRIPTION=API for translating text in manga/manhwa/manhua images
DEBUG=false
HOST=0.0.0.0
PORT=8000

ENABLE_CORS=true
ALLOWED_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"]

ENABLE_RATE_LIMITING=true
TRANSLATION_RATE_LIMIT_REQUESTS=10
TRANSLATION_RATE_LIMIT_WINDOW=5
PREVIEW_RATE_LIMIT_REQUESTS=20
PREVIEW_RATE_LIMIT_WINDOW=5
BATCH_RATE_LIMIT_REQUESTS=2
BATCH_RATE_LIMIT_WINDOW=10

MANGA_OCR_ENABLED=true
EASYOCR_GPU=false

GOOGLE_TRANSLATE_ENABLED=true
DEEPL_ENABLED=false

DEEPL_API_KEY=your-actual-api-key
DEEPL_API_URL=https://api-free.deepl.com/v2/translate

TRANSLATION_TIMEOUT=30
TRANSLATION_MAX_RETRIES=2
TRANSLATION_RETRY_DELAY=1.0

LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_PATH=ink_translator.log
LOG_MAX_SIZE_MB=100
LOG_BACKUP_COUNT=5

MAX_WORKERS=4
ASYNC_TIMEOUT=300

ENABLE_DOCS=true

RELOAD=false

**▶️ Run the Server**
uvicorn main:app --reload

By default, the backend runs at
👉 http://127.0.0.1:8000

### 3️⃣ Frontend Setup (React + Supabase)
**Install Node Dependencies**
cd ../frontend
npm install

**🔐 Environment Variables**

Create a .env file inside frontend/

VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-public-supabase-key
VITE_GOOGLE_CLIENT_ID=your-project-google-client-id


**▶️ Run the Frontend**
npm run dev

By default, the app runs at
👉 http://localhost:5173

The frontend communicates with the backend on port 8000.

# Usage Guide

Sign up or log in via Supabase.

Upload a manga panel image (.jpg or .png).

The backend automatically:

Detects text areas (via Manga-OCR and EasyOCR)

Translates the text using Google Translate API

Renders translated text on the image

Preview or download the translated page.

# Author

Miya Dang
