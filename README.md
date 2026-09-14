# SIH Project

A full-stack application with a **FastAPI** backend and a **Next.js** frontend.

## Project Structure

\\\
sih/
+-- backend/          # FastAPI Python backend
¦   +-- venv/         # Python virtual environment
¦   +-- main.py       # FastAPI application entry point
¦   +-- requirements.txt
+-- frontend/         # Next.js frontend with Tailwind CSS
+-- data/             # Directory for storing PDF files
\\\

## Backend Setup

\\\ash
cd backend
venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn main:app --reload
\\\

API will be available at: http://localhost:8000  
Swagger docs at: http://localhost:8000/docs

## Frontend Setup

\\\ash
cd frontend
npm install
npm run dev
\\\

App will be available at: http://localhost:3000
