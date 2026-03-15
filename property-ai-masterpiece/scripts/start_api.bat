@echo off
cd /d %~dp0..
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
