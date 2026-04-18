@echo off
cd /d %~dp0
python summarize_and_send.py >> logs\pipeline.log 2>&1
