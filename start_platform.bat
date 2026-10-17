@echo off
title NeuralRAG AI Document Chat Platform (FastAPI + Next.js)
echo ============================================================================
echo   NeuralRAG v2.0 — Commercial AI Document Intelligence Platform
echo   CRISP + Multi-File RAG + Corrective RAG (CRAG) + Gemini Model Selector
echo ============================================================================
echo.
echo [1/2] Starting FastAPI Backend Server on http://127.0.0.1:8000 ...
start "NeuralRAG FastAPI Backend" cmd /k "py -3.10 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Next.js Frontend Workspace on http://localhost:3000 ...
cd /d "%~dp0frontend"
start "NeuralRAG Next.js Frontend" cmd /k "npm run dev"

echo.
echo Both servers are launching!
echo   - Frontend UI:     http://localhost:3000
echo   - Backend API Docs: http://127.0.0.1:8000/docs
echo.
pause
