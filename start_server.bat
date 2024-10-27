@echo off
cd /d "%~dp0"

start cmd /k "cd /d %~dp0 && call myvenv\Scripts\activate && cd filetransfer && waitress-serve --port=8000 filetransfer.wsgi:application"

start cmd /k "cd /d %~dp0\frontend && npm start"

start cmd /k "cd /d %~dp0\nginx-rtmp-win32-1.2.1 && start nginx"
    