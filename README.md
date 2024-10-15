Currently can access the whole file system from any device with browser
1. Can download files 
2. Can download directory (auto zipping)
3. Thumbnails generated when browsing
4. Can stream any media file
5. Can stream your desktop screen with OBS
6. can upload files (500 max limit at once in browser)

To Do:
1. User accounts for security and access control of files
2. Theatre mode for streaming platform like UI
3. Terminal access
4. Ffmpeg utilities

[To run open terminal in dserver -] 

source myvenv/Scripts/activate
cd filetransfer
waitress-serve --port=8000 filetransfer.wsgi:application

[clone this library using ]
git clone https://github.com/illuspas/nginx-rtmp-win32

[Run nginx.exe]
