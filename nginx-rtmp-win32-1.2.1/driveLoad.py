import ctypes
import string
import os
import socket
import json


def load_setup_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config


def get_local_ip():
    try:
        # Create a dummy socket and connect to a non-routable address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Use a non-routable address to identify the active interface
            s.connect(("192.168.0.1", 1))  # Common LAN address, no actual connection needed
            ip_address = s.getsockname()[0]
        return ip_address
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return "127.0.0.1"  # Fallback to localhost

# Example usage
local_ip = get_local_ip()

def get_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1
    return drives



def generate_nginx_config(drives, output_file, workDrive):
    with open(output_file, 'w') as f:
        # Write the initial part of the configuration, including the `http` block header
        f.write(
f"""worker_processes  1;
error_log  logs/error.log debug;
events {{
    worker_connections  1024;
}}

rtmp {{
    server {{
        listen 1935;

        application live {{
            live on;
            hls on;  # Enable HLS for the live stream
            hls_path D:/temphls;  # Ensure this path exists
            hls_fragment 4s;  # Set the fragment length
            hls_playlist_length 6s;  # Set the playlist length
            record off;  # Disable recording (optional)
        }}
        
        application hls {{
            live on;
            hls on;  
            hls_path temp/hls;  
            hls_fragment 8s;  
        }}
    }}
}}

http {{
    include       mime.types;
    default_type  application/octet-stream;
    client_body_timeout 300;
    client_header_timeout 300;
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    server_tokens   off;
    keepalive_timeout  65;
    error_log logs/error.log debug;
    types_hash_max_size 2048;

    #change to your own servers IP
    upstream django_server {{
        server {local_ip}:8000;  # Waitress will run on port 8000
    }}

    server {{
        listen       80;
        server_name  localhost;

        # Serve static files
        location /static/ {{
            alias C:/Users/rajka/Desktop/projects/dserver/frontend/build/static/;
        }}

        location /django_static/ {{
            alias C:/Users/rajka/Desktop/projects/dserver/filetransfer/static/;
        }}

        location /api/ {{
            proxy_pass http://django_server;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            client_max_body_size 1000M;  # Increase maximum allowed request size
            proxy_read_timeout 1200s;    # Set proxy read timeout to 1200 seconds
            proxy_send_timeout 1200s;    # Set proxy send timeout to 1200 seconds
            proxy_buffering off;         # Disable buffering for better streaming performance
        }}

        # Serve media files
        location /media/ {{
            alias C:/Users/rajka/Desktop/projects/dserver/filetransfer/static/media/;
        }}

        # Serve downloads directly
        location / {{
            root C:/Users/rajka/Desktop/projects/dserver/frontend/build/;
            try_files $uri /index.html;
        }}

        # Proxy WebSocket connections to Node.js (for real-time updates)
        location /socket.io/ {{
            proxy_pass http://127.0.0.1:3000;  # Node.js runs on port 3000
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }}
""")

        # Dynamically add location blocks for each drive
        for drive in drives:
            f.write(f"""
        location /stream/{drive}/ {{
            alias {drive}:/;
            add_header Accept-Ranges bytes;
            add_header Cache-Control "public, max-age=3600";
        }}
""")
            f.write(f"""
        location /downloads/{drive}/ {{
            alias {drive}:/;
            add_header Content-Disposition 'attachment' always;
            add_header Accept-Ranges bytes;
            add_header Cache-Control "public, max-age=3600";

            if (-d $request_filename) {{
                return 403;
            }}
        }}
""")

        # Additional configuration sections using workDrive
        f.write(f"""
        location /temparchive/ {{
            alias {workDrive}:/temparchive/;
            autoindex on;  # Temporarily enable for testing
            try_files $uri $uri/ =404;
            add_header Accept-Ranges bytes;
            add_header Content-Disposition "attachment; filename=$request_filename";
            add_header Cache-Control "no-cache";
            proxy_buffering off;
        }}

        location /transfer/thumbnails/ {{
            alias {workDrive}:/temp_thumbnails/;
        }}

        location /hls {{
            types {{
                application/vnd.apple.mpegurl m3u8;
                video/mp2t ts;
            }}
            alias {workDrive}:/temphls;
            add_header Cache-Control no-cache;
        }}

        location /thumbnails/ {{
            alias {workDrive}:/serverthumb/;
            autoindex on;
        }}
""")

        # Close the `http` block
        f.write("    }\n}\n")
    print(f"Nginx configuration generated at {output_file}")


if __name__ == '__main__':
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Assuming nginx.conf is in a 'conf' subdirectory relative to the script
    nginx_conf_dir = os.path.join(script_dir, 'conf')

    # Output file path for the generated configuration
    output_file = os.path.join(nginx_conf_dir, 'nginx.conf')

    setup_file = os.path.abspath(os.path.join(
        script_dir, '..', 'setup.json'))
    try:
        with open(setup_file, 'r') as f:
            config = json.load(f)
        workDrive = config.get("drive_letter")
    except FileNotFoundError:
        print("Error: setup.json file not found. Please make sure the file exists under /dserver/")
    except json.JSONDecodeError:
        print("Error: setup.json contains invalid JSON. Please ensure it is properly formatted and includes a 'drive_letter' setting.")
    except KeyError:
        print("Error: 'drive_letter' not found in setup.json. Please ensure you have set it up.")

    drives = get_drives()
    print(drives)
    generate_nginx_config(drives, output_file, workDrive=workDrive)
