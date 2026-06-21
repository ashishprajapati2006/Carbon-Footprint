# 🌱 EcoPilot AI – Unified Green Platform

EcoPilot AI is a state-of-the-art carbon footprint tracking, analytics, and lifestyle-coaching web application. It empowers users to monitor their carbon impact, scan utility statements, perform visual appliance audits, run carbon simulations, and receive personalized recommendations backed by AI.

🔗 **Live Application URL:** [https://carbon-footprint-dun.vercel.app/](https://carbon-footprint-dun.vercel.app/)

---

## 🌟 Core Features

- **📊 Central Dashboard**: Track real-time carbon offsets, monthly CO₂ levels, predictions, and recent green activities in a beautiful glassmorphic interface.
- **💬 AI Sustainability Coach**: Engage in chat threads with an AI assistant powered by **Gemini 2.5 Flash** for customized advice on reducing emissions, diet shifts, and transport.
- **🧾 Bill Statement Scanner**: Extract metrics (kWh consumed, charges, billing periods) from utility bills using OCR and Gemini Multimodal analysis to track carbon footprints automatically.
- **🔍 EcoVision Room Auditor**: Audit room appliances from uploaded photos to estimate energy waste, carbon impact, and receive smart energy alternatives.
- **🌐 Carbon Twin Simulator**: Run interactive, real-time lifestyle simulations (e.g., swapping to an EV, installing solar panels, reducing flights) to visualize projected CO₂ drops.
- **🏆 Gamification & Leaderboard**: Earn XP and unlock badges for adopting green habits, and compare progress on the global leaderboard.

---

## 🛠️ Technology Stack

### Frontend
- **Framework**: Next.js 14+ (React, TypeScript, App Router)
- **Styling**: Tailwind CSS with custom HSL dark-mode themes
- **Animations**: Framer Motion for premium micro-animations
- **Icons**: Lucide React

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Async DB Driver**: Motor (MongoDB Async Driver)
- **Security**: PyJWT (JSON Web Tokens) & Passlib (Bcrypt hashing)
- **AI/LLM**: Google GenAI SDK (utilizing `gemini-2.5-flash`)
- **Data Science**: Pandas, NumPy, Scikit-Learn (for trend predictions)

### Database
- **Database**: MongoDB (Atlas in production, with a seamless in-memory Mock Database fallback for development testing)

---

## 📁 Project Directory Structure

```
├── backend/                    # FastAPI application
│   ├── ai/                     # Gemini AI client & prompt services
│   ├── api/                    # REST API routes (auth, coach, twin, etc.)
│   ├── controllers/            # Request controllers and orchestration
│   ├── core/                   # Config validation & Database client managers
│   ├── middleware/             # Rate-limiters and security filters
│   ├── ml/                     # ML training, data sets, and predictors
│   ├── models/                 # ML serialized files
│   ├── ocr/                    # OCR statement extractors
│   ├── repositories/           # Database access layer (MongoDB CRUD)
│   ├── schemas/                # Pydantic input/output validation schemas
│   ├── services/               # Core business services
│   ├── tests/                  # Automated unit and integration test suites
│   ├── main.py                 # FastAPI server entry point
│   └── requirements.txt        # Python dependency manifest
├── frontend/                   # Next.js frontend application
│   ├── app/                    # Pages & routing layouts (App Router)
│   ├── components/             # Reusable UI components (charts, lists, etc.)
│   ├── hooks/                  # Custom React hooks
│   ├── lib/                    # Client library wrappers
│   ├── public/                 # Static assets (images, icons)
│   ├── services/               # Frontend API service layer (fetch/auth)
│   ├── types/                  # TypeScript interface definitions
│   └── package.json            # Node.js dependencies & scripts
├── docker-compose.yml          # Container configuration for local stack
└── README.md                   # Project documentation
```

---

## ⚙️ Configuration & Environment Setup

The application uses environment variables for configuration. You need to configure them for both the backend and the frontend.

### 1. Backend Environment Setup (`backend/.env`)
Create a `.env` file inside the `backend/` folder and populate it with the following parameters:

```env
# MongoDB - Set to "dummy" to run in-memory Mock DB mode without a running Mongo instance
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/ecopilot

# Security
JWT_SECRET=your_super_secret_jwt_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Gemini API
GEMINI_API_KEY=your_gemini_api_key_from_google_ai_studio

# Service URLs
NEXT_PUBLIC_API_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

# Environment Mode
ENVIRONMENT=development
```

### 2. Frontend Environment Setup (`frontend/.env.local`)
Create a `.env.local` file inside the `frontend/` folder:

```env
# URL pointing to the FastAPI backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🚀 Running the Project Locally

### Option A: Manual Setup (Development)

#### Step 1: Run the Backend
Ensure you have Python 3.10+ installed.
```bash
cd backend
python -m venv venv
# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --reload
```
The backend server will run on `http://127.0.0.1:8000`.

#### Step 2: Run the Frontend
Ensure you have Node.js 18+ installed.
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser to view the application.

---

### Option B: Docker Compose (All-in-One)
To spin up the frontend, backend, and local MongoDB server simultaneously in containers, run the following from the root directory:
```bash
docker-compose up --build
```
- **Frontend URL:** `http://localhost:3000`
- **Backend API URL:** `http://localhost:8000`
- **MongoDB Instance:** `mongodb://localhost:27017`

---

## 🧪 Running Automated Tests
The backend contains a test suite covering authentication, predictions, bill scanning, and caching.
To run the tests:
```bash
cd backend
# Run a specific suite
python tests/test_auth.py
# Run all unit tests
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🌐 Production Deployment

### Frontend (Vercel)
- The frontend is optimized to build and deploy on **Vercel**.
- Configure the environment variable `NEXT_PUBLIC_API_URL` in the Vercel dashboard to point to your deployed Render backend URL.

### Backend (Render)
- The backend runs on a **Render Web Service**.
- In the Render dashboard, define the environment variables (`MONGODB_URI`, `GEMINI_API_KEY`, `JWT_SECRET`, etc.) inside the service's Environment settings.
