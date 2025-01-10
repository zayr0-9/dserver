Currently can access the whole file system from any device with browser

1. Can download files
2. Can download directory (auto zipping)
3. Thumbnails generated when browsing
4. Can stream any media file
5. Can stream your desktop screen with OBS
6. can upload files (500 max limit at once in browser)
7. Launchserver.exe
8. Populate drives dynamically in nginx conf
9. Implemented monaco code editor
10. Automate setup

To Do:

1. User accounts for security and access control of files (basic version exists now)
2. Theatre mode for streaming platform like UI (need to polish more but basic functionality implemented)
3. Terminal access
4. Ffmpeg utilities
5. Implement RTP streaming
6. Implement simple music and video file editing (cropping, concatenating etc)
7. Implement remote desktop control

[To run open terminal in dserver -]

1. source myvenv/Scripts/activate
2. cd filetransfer
3. waitress-serve --port=8000 filetransfer.wsgi:application

[nginx rtmp]

1. nginx rtmp source - https://github.com/illuspas/nginx-rtmp-win32

[Run nginx.exe]

Attention! - nginx-rtmp-win32-1.2.1 folder will not contain logs folder and fail to run. Create an empty folder named "logs" to fix it. Self nginx installation from source doesn't have this issue.
