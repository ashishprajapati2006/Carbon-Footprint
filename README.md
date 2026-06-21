# EcoPilot AI – Unified Green Platform

EcoPilot AI is a carbon-footprint tracking, analytics, and lifestyle-coaching application built with Next.js (frontend) and FastAPI (backend).

## Project Structure

```
backend/           # FastAPI application
  api/             # API routes
  controllers/     # Request controllers
  services/        # Business logic services
  repositories/    # Data persistence layer
  models/          # ML model artifacts
  schemas/         # Pydantic schemas
  middleware/      # Custom middleware modules
  core/            # Core configuration & database manager
  utils/           # Utility helpers
  ai/              # Gemini AI client
  ml/              # ML training, evaluation, and predictors
  ocr/             # OCR statement extraction and appliance visual audit
  tests/           # Automated test suites
  main.py          # FastAPI application entry point
  requirements.txt # Python package dependencies
frontend/          # Next.js frontend application
  app/             # Pages and layouts (App Router)
  components/      # Reusable UI components
  hooks/           # Custom React hooks
  services/        # API client modules
  lib/             # Library wrappers
  types/           # TypeScript types definitions
  public/          # Static assets
  package.json     # Node.js configuration
docs/              # Project documentation
scripts/           # Automation scripts
models/            # Root model directory
uploads/           # Temp file uploads directory
.github/           # GitHub Actions workflows
```

## Running the Project

### 1. Configure Environments
Create a `.env` file inside `backend/` using the keys defined in `.env.example`.

### 2. Start Backend
```bash
cd backend
python -m uvicorn main:app --reload
```

### 3. Start Frontend
```bash
cd frontend
npm run dev
```
