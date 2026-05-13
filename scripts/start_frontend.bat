@echo off
cd /d %~dp0\..\frontend
echo Starting MatchFlow Analytics Frontend...
npm install
npm run dev
