import ctypes
import string
import os
import subprocess
import json


def load_setup_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config


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
        # Generate configuration for each drive
        for drive in drives:
            f.write(f"""
    location /stream/{drive}/ {{
        alias {drive}:/;
        add_header Accept-Ranges bytes;
        add_header Cache-Control "public, max-age=3600";
    }}
""")
        for drive in drives:
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
        # internal;
        alias {workDrive}:/temparchive/;
        autoindex on;  # Temporarily enable for testing
        try_files $uri $uri/ =404;
        add_header Accept-Ranges bytes;
        add_header Content-Disposition "attachment; filename=$request_filename";
        add_header Cache-Control "no-cache";
        # Optionally set buffer size
        proxy_buffering off;
    }}

    # Serve thumbnails directly
    location /transfer/thumbnails/ {{
        alias {workDrive}:/temp_thumbnails/;  # Adjust the path to your thumbnails directory
    }}

    location /hls {{
        types {{
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }}
        alias {workDrive}:/temphls;  # HLS output directory
        add_header Cache-Control no-cache;
    }}

    location /thumbnails/ {{
        alias {workDrive}:/serverthumb/;  # Update this with the actual path to your thumbnails directory
        autoindex on;  # Optional: allow directory listing if needed
    }}
""")
    print(f"Nginx configuration generated at {output_file}")


if __name__ == '__main__':
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Assuming nginx.conf is in a 'conf' subdirectory relative to the script
    nginx_conf_dir = os.path.join(script_dir, 'conf')

    # Output file path for the generated configuration
    output_file = os.path.join(nginx_conf_dir, 'dynamic_drives.conf')

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
