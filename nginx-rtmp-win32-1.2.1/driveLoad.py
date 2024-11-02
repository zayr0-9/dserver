import ctypes
import string
import os
import subprocess


def get_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1
    return drives


def generate_nginx_config(drives, output_file):
    with open(output_file, 'w') as f:
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
    print(f"Nginx configuration generated at {output_file}")


if __name__ == '__main__':
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Assuming nginx.conf is in a 'conf' subdirectory relative to the script
    nginx_conf_dir = os.path.join(script_dir, 'conf')

    # Output file path for the generated configuration
    output_file = os.path.join(nginx_conf_dir, 'dynamic_drives.conf')

    drives = get_drives()
    generate_nginx_config(drives, output_file)
