
from math import ceil
from threading import Thread
import glob
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect, FileResponse, JsonResponse, StreamingHttpResponse
import os
import datetime
import time
from django.views.decorators.http import require_POST
import hashlib
import subprocess
import json
from PIL import Image
import threading
from urllib.parse import quote
from transfer.models import FileSearchMetadata, Movie, FileLock, FileTypeCategory
from django.db.models import Q
from .models import Directory, Movie
from django.views.decorators.csrf import csrf_exempt
import logging
from pathlib import Path
from urllib.parse import unquote, quote
import string
from ctypes import windll
from django.conf import settings
from .forms import FileTypeCategoryForm
import logging
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

# logger = logging.getLogger(__name__)


# BASE_DIR = 'C:\\'  # Change this to the base directory you want to start with
ADMIN_PIN = "12345"


logger = logging.getLogger(__name__)


@require_POST
def api_login(request):
    import json
    data = json.loads(request.body)
    username = data.get('username')
    password = data.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'error': 'Invalid credentials'}, status=401)


@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({'success': True})


@ensure_csrf_cookie
def get_csrf_token(request):
    # This view just triggers the setting of the CSRF cookie
    return JsonResponse({'success': True})


def file_upload(request, base_dir, relative_path):
    """
    Handle file uploads to the specified directory.
    """
    logger.debug(
        f"Received file upload request: base_dir={base_dir}, relative_path={relative_path}")

    # Sanitize base_dir and relative_path to prevent directory traversal
    base_dir = os.path.normpath(base_dir)
    relative_path = os.path.normpath(relative_path)

    # Prevent directory traversal
    if '..' in base_dir or '..' in relative_path:
        logger.warning("Directory traversal attempt detected.")
        return JsonResponse({'error': 'Invalid directory path.'}, status=400)
    if not relative_path:
        logger.warning("Didnt recieve relative path.")
        return JsonResponse({'error': 'Invalid directory path.'}, status=400)
    # Handle empty relative_path
    if relative_path in ('', '.'):
        relative_path = 'Uploads'  # Default upload directory, adjust as needed

    # Construct the absolute upload directory path
    if os.name == 'nt':  # Windows
        upload_dir = f"{base_dir}:\\{relative_path}"
    else:  # Unix/Linux
        upload_dir = os.path.join(base_dir, relative_path)

    logger.debug(f"Constructed upload directory path: {upload_dir}")

    # Ensure the upload directory exists
    try:
        os.makedirs(upload_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create upload directory: {e}")
        return JsonResponse({'error': 'Failed to create upload directory.'}, status=500)

    # Check write permissions
    if not os.access(upload_dir, os.W_OK):
        logger.error(f"No write permission for directory: {upload_dir}")
        return JsonResponse({'error': 'No write permission for the specified directory.'}, status=403)

    if 'files' not in request.FILES:
        logger.warning("No files found in the request.")
        return JsonResponse({'error': 'No files uploaded'}, status=400)

    files = request.FILES.getlist('files')
    uploaded_files = []

    for file in files:
        filename = file.name

        # Validate file extension
        ext = os.path.splitext(filename)[1].lower()
        # if ext not in ALLOWED_EXTENSIONS:
        #     logger.warning(f"Attempt to upload disallowed file type: {filename}")
        #     return JsonResponse({'error': f'File type {ext} not allowed.'}, status=400)

        # Prevent uploading files with absolute paths
        if os.path.isabs(filename):
            logger.warning(
                f"Attempt to upload file with absolute path: {filename}")
            return JsonResponse({'error': 'Invalid file name.'}, status=400)

        # Construct the full file path
        file_path = os.path.join(upload_dir, filename)
        logger.debug(f"Uploading file to: {file_path}")

        try:
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            uploaded_files.append(filename)
            logger.info(f"Successfully uploaded: {file_path}")

            # Set file permissions to read-write for the owner only (Windows)
            if os.name == 'nt':
                import ctypes
                FILE_ATTRIBUTE_NORMAL = 0x80
                ctypes.windll.kernel32.SetFileAttributesW(
                    file_path, FILE_ATTRIBUTE_NORMAL)
            else:
                os.chmod(file_path, 0o600)

        except PermissionError as pe:
            logger.error(f"Permission denied: {pe}")
            return JsonResponse({'error': f'Permission denied for file: {filename}'}, status=403)
        except Exception as e:
            logger.error(f"Error uploading file {filename}: {e}")
            return JsonResponse({'error': f'Error uploading file: {filename}'}, status=500)

    return JsonResponse({'success': True, 'uploaded_files': uploaded_files}, status=200)


def search_files(request):
    search_query = request.GET.get('q', '').strip()  # Get search query
    results = []

    if search_query:
        # Perform a search using ORM with case-insensitive matching
        results = FileSearchMetadata.objects.filter(
            Q(file_name__icontains=search_query) |
            Q(file_path__icontains=search_query)
        )

    return render(request, 'search_results.html', {'results': results, 'query': search_query})


def search_files(request):
    # Get the search query from the request
    query = request.GET.get('q', '').strip()
    thumbnail_size = 500

    # Debug output to see the query and what's being searched
    print(f"Search query: {query}")

    if query:
        # Perform case-insensitive search for both file names and file paths
        results = FileSearchMetadata.objects.filter(
            Q(file_name__icontains=query) | Q(file_path__icontains=query)
        )
    else:
        # No search results if no query is provided
        results = FileSearchMetadata.objects.none()

    context = {
        'items': results,
        'thumbnail_size': thumbnail_size,
        'query': query,
    }
    return render(request, 'search_results.html', context)


def drives(request):
    drives = get_drives()
    context = {
        'drives': drives,
    }
    return render(request, 'drivelist.html', context)

# for react spa


@csrf_exempt  # Use with caution; consider implementing proper CSRF handling
def validate_pin_api(request, drive_letter):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

    try:
        data = json.loads(request.body)
        path = data.get('path', '').lstrip('/\\')
        entered_pin = data.get('pin', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    # Validate the PIN
    if entered_pin == ADMIN_PIN:
        # Set a session variable to indicate access
        session_key = f"admin_pin_valid_{drive_letter}_{path}"
        request.session[session_key] = True
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': 'Incorrect PIN. Please try again.'}, status=401)


def get_drives_api(request):
    drives = get_drives()  # Assuming get_drives() returns a list of drive letters
    data = {'drives': drives}
    return JsonResponse(data)


def get_drives():
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1
    return drives


@require_http_methods(["POST"])
def delete_item(request):
    data = json.loads(request.body)
    base_dir = data.get('base_dir')
    relative_path = data.get('relative_path')
    if not base_dir or not relative_path:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    if len(base_dir) == 1 and base_dir.isalpha():
        base_dir = base_dir + ':\\'

    full_path = os.path.normpath(os.path.join(base_dir, relative_path))
    if not full_path.startswith(os.path.abspath(base_dir)):
        return JsonResponse({'error': 'Invalid path'}, status=400)

    if not os.path.exists(full_path):
        return JsonResponse({'error': 'File or directory does not exist'}, status=404)

    # begin deletion
    try:
        if os.path.isfile(full_path):
            os.remove(full_path)
        elif os.path.isdir(full_path):
            os.rmdir(full_path)
        else:
            return JsonResponse({'error': 'Unknown file type'}, status=400)
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error deleting item at {full_path}: {e}")
        return JsonResponse({'error': 'Error deleting item'}, status=400)

# helper function for TextEditor


file_locks = {}  # temporary move to database
LOCK_TIMEOUT = 300  # Lock expires after 5 minutes


def clean_expired_locks():
    current_time = time.time()
    with threading.Lock():
        for lock_key in list(file_locks.keys()):
            lock_info = file_locks[lock_key]
            if current_time - lock_info['timestamp'] > LOCK_TIMEOUT:
                del file_locks[lock_key]


@require_POST
def get_file_content(request):
    data = json.loads(request.body)
    base_dir = data.get('base_dir')
    relative_path = data.get('relative_path')

    if not base_dir or not relative_path:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    # Adjust base_dir as needed
    if os.name == 'nt' and len(base_dir) == 1 and base_dir.isalpha():
        base_dir = base_dir + ':\\'

    full_path = os.path.normpath(os.path.join(base_dir, relative_path))

    # Security checks
    if not os.path.isfile(full_path):
        return JsonResponse({'error': 'File does not exist'}, status=404)

    # Prevent directory traversal
    if not full_path.startswith(os.path.abspath(base_dir)):
        return JsonResponse({'error': 'Invalid path'}, status=400)

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        file_name = os.path.basename(full_path)
        return JsonResponse({'success': True, 'content': content, 'name': file_name})
    except Exception as e:
        logger.error(f"Error reading file at {full_path}: {e}")
        return JsonResponse({'error': 'Error reading file'}, status=500)


def is_text_file(file_path):
    # logger.debug(f"checking if file is text at path : {file_path}")
    text_extensions = ['.txt', '.py', '.js', '.html', '.css',
                       '.json', '.md', '.java', '.c', '.cpp']  # Extend as needed

    # logger.debug(os.path.splitext(file_path)[1].lower()
    #              )
    return os.path.splitext(file_path)[1].lower() in text_extensions


@require_POST
def save_file_content(request):
    data = json.loads(request.body)
    base_dir = data.get('base_dir')
    relative_path = data.get('relative_path')
    content = data.get('content')

    if not base_dir or not relative_path or content is None:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    # Adjust base_dir as needed
    if os.name == 'nt' and len(base_dir) == 1 and base_dir.isalpha():
        base_dir = base_dir + ':\\'

    full_path = os.path.normpath(os.path.join(base_dir, relative_path))

    # Security checks
    if not full_path.startswith(os.path.abspath(base_dir)):
        return JsonResponse({'error': 'Invalid path'}, status=400)

    # Optional: Check if the user has write permissions
    if not os.access(full_path, os.W_OK):
        return JsonResponse({'error': 'No write permission for this file'}, status=403)

    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error writing to file at {full_path}: {e}")
        return JsonResponse({'error': 'Error saving file'}, status=500)
# @require_GET


def file_list_api(request, drive_letter):
    logger.debug("Testing logging configuration.")
    base_dir = unquote(drive_letter)
    path = unquote(request.GET.get('path', '')).lstrip('/\\')

    # Boolean to control whether hidden files are shown
    show_hidden_files = False  # Default is False; can be updated from admin settings

    # Sorting parameters
    sort_by = request.GET.get('sort_by', 'name')  # Default sort by name
    sort_dir = request.GET.get('sort_dir', 'asc')  # Default ascending order

    # Filtering parameters
    filter_type = request.GET.get('type', 'all')  # 'all', 'dir', 'file'
    size_min = request.GET.get('size_min')
    size_max = request.GET.get('size_max')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    sub_file_type = request.GET.get('file_type', 'all')  # Sub-file type filter

    # Pagination parameters
    try:
        page = int(request.GET.get('page', '1'))
        page_size = int(request.GET.get('page_size', '100'))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
        page_size = 100

    # Define file type extensions
    FILE_TYPES = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
        'videos': ['.mp4', '.avi', '.mov', '.webm', '.mkv'],
        'documents': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'],
        'audio': ['.mp3', '.wav', '.aac', '.flac'],
        'archives': ['.zip', '.rar', '.7z', '.tar', '.gz']
    }

    if not base_dir:
        return JsonResponse({'error': 'Base directory not specified'}, status=400)

    base_dir_with_drive = f"{base_dir}:\\"
    full_path = os.path.normpath(os.path.join(base_dir_with_drive, path))

    if not os.path.exists(full_path):
        raise Http404("Directory does not exist")

    if not full_path.startswith(os.path.normpath(base_dir_with_drive)):
        raise Http404("Access denied")

    # Check if the directory is private (Assuming Directory model exists)
    # directory_entry = Directory.objects.filter(path=full_path).first()
    # session_key = f"admin_pin_valid_{base_dir}_{path}"
    # Implement access control as needed

    # Default size is 100x100 for thumbnails
    thumbnail_size = 100
    temp_dir = os.path.join(settings.BASE_DIR, 'temp_thumbnails')
    os.makedirs(temp_dir, exist_ok=True)

    items = []
    with os.scandir(full_path) as entries:
        for entry in entries:
            # Skip hidden files if show_hidden_files is False
            if not show_hidden_files and entry.name.startswith('.'):
                continue

            item_name = entry.name
            item_path = entry.path
            is_dir = entry.is_dir(follow_symlinks=False)
            try:
                stat = entry.stat(follow_symlinks=False)
            except FileNotFoundError:
                continue  # Skip if file was removed during scanning
            size = stat.st_size if not is_dir else None
            modified = datetime.datetime.fromtimestamp(
                stat.st_mtime).isoformat()
            created = datetime.datetime.fromtimestamp(
                stat.st_ctime).isoformat()
            relative_path = os.path.join(path, item_name).replace('\\', '/')
            file_ext = os.path.splitext(item_name)[1].lower()

            # Determine if the file is a video
            video_extensions = tuple(FILE_TYPES['videos'])
            is_video = not is_dir and file_ext in video_extensions

            item_info = {
                'name': item_name,
                'path': path,
                'relative_path': relative_path,
                'is_dir': is_dir,
                'size': size,
                'modified': modified,
                'created': created,
                'thumbnail': None,
                'is_video': is_video,
                'is_text': is_text_file(item_name),
            }

            # Generate thumbnails for images
            if not is_dir and file_ext in FILE_TYPES['images']:
                try:
                    # Thumbnail file name based on size
                    file_identifier = f"{item_path}_{int(stat.st_mtime)}_{thumbnail_size}"
                    thumbnail_hash = hashlib.md5(
                        file_identifier.encode('utf-8')).hexdigest()
                    thumbnail_ext = '.png' if file_ext == '.png' else '.jpg'
                    thumbnail_filename = f"thumb_{thumbnail_hash}{thumbnail_ext}"
                    thumbnail_path = os.path.join(temp_dir, thumbnail_filename)

                    # Generate thumbnail if it doesn't exist
                    if not os.path.exists(thumbnail_path):
                        with Image.open(item_path) as image:
                            image.thumbnail((thumbnail_size, thumbnail_size))
                            image_format = 'PNG' if image.mode == 'RGBA' else 'JPEG'
                            image.save(thumbnail_path, image_format)

                    item_info['thumbnail'] = thumbnail_filename
                except Exception as e:
                    logger.error(
                        f"Failed to create thumbnail for {item_name}: {e}")

            # Generate thumbnails for videos
            elif not is_dir and file_ext in FILE_TYPES['videos']:
                try:
                    # Thumbnail file name based on size
                    file_identifier = f"{item_path}_{int(stat.st_mtime)}_{thumbnail_size*10}"
                    thumbnail_hash = hashlib.md5(
                        file_identifier.encode('utf-8')).hexdigest()
                    thumbnail_filename = f"thumb_{thumbnail_hash}.jpg"
                    thumbnail_path = os.path.join(temp_dir, thumbnail_filename)

                    # Generate thumbnail if it doesn't exist
                    if not os.path.exists(thumbnail_path):
                        # Use ffmpeg to extract a frame at 00:00:01
                        command = [
                            'ffmpeg',
                            '-y',
                            '-i', item_path,
                            '-ss', '00:00:01',
                            '-vframes', '1',
                            '-vf', f'scale={thumbnail_size}:-1',
                            thumbnail_path
                        ]
                        subprocess.run(
                            command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

                    item_info['thumbnail'] = thumbnail_filename
                except Exception as e:
                    logger.error(
                        f"Failed to create video thumbnail for {item_name}: {e}")

            items.append(item_info)

    # Apply filtering
    filtered_items = []
    for item in items:
        # Apply sub-file type filter first
        if sub_file_type != 'all' and not item['is_dir']:
            file_ext = os.path.splitext(item['name'])[1].lower()
            if file_ext not in FILE_TYPES.get(sub_file_type, []):
                continue  # Skip files that don't match the selected sub-type

        # Then filter by type (dir, file, all)
        if filter_type == 'dir' and not item['is_dir']:
            continue
        if filter_type == 'file' and item['is_dir']:
            continue

        # Filter by size
        if size_min and item['size'] is not None and item['size'] < int(size_min):
            continue
        if size_max and item['size'] is not None and item['size'] > int(size_max):
            continue

        # Filter by date
        if date_from:
            date_from_dt = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            item_modified_dt = datetime.datetime.fromisoformat(
                item['modified'])
            if item_modified_dt < date_from_dt:
                continue
        if date_to:
            date_to_dt = datetime.datetime.strptime(date_to, '%Y-%m-%d')
            item_modified_dt = datetime.datetime.fromisoformat(
                item['modified'])
            if item_modified_dt > date_to_dt:
                continue

        filtered_items.append(item)

    # Apply sorting
    reverse = (sort_dir == 'desc')

    # Define sort key function
    def sort_key(item):
        key = item.get(sort_by)
        if key is None:
            if sort_by == 'size':
                return 0
            return ""
        return key

    # Ensure directories are listed first
    filtered_items.sort(
        key=lambda item: (not item['is_dir'], sort_key(item)),
        reverse=reverse
    )

    # Pagination
    total_items = len(filtered_items)
    total_pages = (total_items + page_size - 1) // page_size
    if page > total_pages and total_pages != 0:
        page = total_pages
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_items = filtered_items[start_index:end_index]

    response_data = {
        'items': paginated_items,
        'current_path': path,
        'base_dir': base_dir,
        'thumbnail_size': thumbnail_size,
        'is_private': False,  # Update based on access control
        'q': request.GET.get('q', ''),
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'filter_type': filter_type,
        'file_type': sub_file_type,
        'size_min': size_min,
        'size_max': size_max,
        'date_from': date_from,
        'date_to': date_to,
        'pagination': {
            'current_page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'total_items': total_items,
        }
    }
    return JsonResponse(response_data)


def get_latest_mtime(directory):
    latest_mtime = 0
    for root, dirs, files in os.walk(directory):
        for fname in files:
            fpath = os.path.join(root, fname)
            mtime = os.path.getmtime(fpath)
            if mtime > latest_mtime:
                latest_mtime = mtime
    return latest_mtime


def download_zip(request):
    logger.debug("download_zip view called.")
    relative_path = request.GET.get('path', '')
    base_dir = request.GET.get('base_dir')
    logger.debug(
        f"Received base_dir: {base_dir}, relative_path: {relative_path}")

    # Adjust base_dir for Windows drive letters
    if os.name == 'nt' and len(base_dir) == 1 and base_dir.isalpha():
        base_dir = base_dir + ':\\'
    logger.debug(f"Adjusted base_dir: {base_dir}")

    full_path = os.path.normpath(os.path.join(base_dir, relative_path))
    logger.debug(f"Constructed full_path: {full_path}")

    # Prevent directory traversal attacks
    if not full_path.startswith(os.path.normpath(base_dir)):
        logger.warning("Directory traversal attempt detected.")
        raise Http404("Invalid path")

    if not os.path.exists(full_path):
        logger.error(f"Path does not exist: {full_path}")
        raise Http404("Directory does not exist")

    if not os.path.isdir(full_path):
        logger.error(f"Path is not a directory: {full_path}")
        raise Http404("Directory does not exist")

    dir_name = os.path.basename(os.path.normpath(full_path))
    zip_filename = f"{dir_name}.zip"
    zip_dir = os.path.join(settings.BASE_DIR, 'temparchive')
    os.makedirs(zip_dir, exist_ok=True)
    zip_path = os.path.join(zip_dir, zip_filename)

    # Determine whether to create or reuse the zip file
    regenerate_zip = False
    # Use 7z to create the zip file
    try:
        subprocess.check_call(
            ['7z', 'a', '-tzip', '-mx=0', zip_path, full_path]
        )
        logging.info(f"Zip file created at {zip_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating zip file: {e}")
        return HttpResponse("Error creating zip file.", status=500)
    if os.path.exists(zip_path):
        # Get the modification time of the zip file
        zip_mtime = os.path.getmtime(zip_path)

        # Get the latest modification time in the directory
        dir_mtime = get_latest_mtime(full_path)

        if dir_mtime > zip_mtime:
            regenerate_zip = True
    else:
        regenerate_zip = False

    if regenerate_zip:
        # Remove the old zip file if it exists
        if os.path.exists(zip_path):
            os.remove(zip_path)

        # Use 7z to create the zip file
        try:
            subprocess.check_call(
                ['7z', 'a', '-tzip', '-mx=0', zip_path, full_path])
        except subprocess.CalledProcessError:
            return HttpResponse("Error creating zip file.", status=500)

    # Construct the URL that Nginx will serve
    zip_url = f"/temparchive/{quote(zip_filename)}"

    # Redirect the user to the zip file URL for Nginx to handle byte-range requests
    return HttpResponseRedirect(zip_url)


# @login_required


def gpu_available():
    # Implement logic to check if GPU encoding is available
    # For example, check if 'hevc_nvenc' is in FFmpeg encoders
    result = subprocess.run(
        ['ffmpeg', '-encoders'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return 'hevc_nvenc' in result.stdout


# @require_GET
@require_GET
def stream_hls(request, drive_letter, path):
    logger.debug(f"Entering Stream HLS {drive_letter}, {path}")
    base_dir = drive_letter + ':\\' if os.name == 'nt' else '/' + drive_letter
    relative_path = unquote(path)
    full_path = os.path.normpath(os.path.join(base_dir, relative_path))

    # Security checks
    if not os.path.isfile(full_path):
        return JsonResponse({'error': 'File does not exist'}, status=404)

    if not full_path.startswith(os.path.abspath(base_dir)):
        return JsonResponse({'error': 'Invalid path'}, status=400)

    # Define HLS output directory
    hls_output_base_dir = 'D:/temp_hls'
    video_identifier = os.path.basename(full_path)
    hls_output_dir = os.path.join(hls_output_base_dir, video_identifier)
    os.makedirs(hls_output_dir, exist_ok=True)

    hls_playlist = os.path.normpath(os.path.join(hls_output_dir, 'index.m3u8'))
    logger.debug(f"Generating HLS chunks at {hls_output_dir}, {hls_playlist}")

    ffmpeg_command = [
        'ffmpeg',
        '-y',
        '-i', full_path,
        '-c:v', 'h264_nvenc' if gpu_available() else 'libx264',
        '-preset', 'fast',
        '-profile:v', 'high',
        '-level:v', '4.1',
        '-pix_fmt', 'yuv420p',  # Ensure 8-bit color depth
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ac', '2',  # Downmix to stereo if necessary
        '-hls_time', '4',
        '-hls_list_size', '0',
        '-hls_flags', 'delete_segments',  # Removed 'append_list'
        '-hls_playlist_type', 'vod',     # Changed to 'vod'
        '-f', 'hls',
        hls_playlist
    ]

    def run_ffmpeg():
        process = subprocess.Popen(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        stderr, _ = process.communicate()
        if process.returncode != 0:
            error_message = stderr.decode('utf-8')
            logger.error(f'FFmpeg error: {error_message}')

    thread = Thread(target=run_ffmpeg)
    thread.daemon = True
    thread.start()

    # Wait for the playlist and initial segments to be created
    max_wait = 30  # seconds
    waited = 0
    while (not os.path.exists(hls_playlist) or len(glob.glob(os.path.join(hls_output_dir, '*.ts'))) < 2) and waited < max_wait:
        time.sleep(30)
        waited += 1

    if not os.path.exists(hls_playlist):
        logger.error('Error generating HLS playlist within timeout')
        return JsonResponse({'error': 'Error generating HLS playlist'}, status=500)

    # Return the playlist URL to the client
    playlist_url = f'/hls/{video_identifier}/index.m3u8'
    response_data = {
        'playlist_url': playlist_url,
        'video_filename': video_identifier,
    }
    logger.debug(f"Returning playlist URL: {playlist_url}")
    return JsonResponse(response_data)


def download_file(request, path, filename):
    file_path = os.path.join(settings.BASE_DIR, path, filename)
    if not os.path.exists(file_path):
        raise Http404("File does not exist")
    # Open the file for streaming the response
    response = FileResponse(open(file_path, 'rb'),
                            as_attachment=True, filename=filename)
    response['Content-Type'] = 'application/octet-stream'
    # Indicate that the server accepts byte-range requests
    response['Accept-Ranges'] = 'bytes'
    return response


def homepage(request):
    PROJECT_ROOT = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    x = os.path.join(PROJECT_ROOT, 'frontend', 'build')
    print(x)
    return render(request, 'homepage.html')


def file_mode(request):
    return redirect('file_list')  # Redirect to the file_list view


def theatre_mode(request):
    return render(request, 'theatre.html')


def admin_pin_entry(request):
    if request.method == 'POST':
        pin = request.POST.get('pin', None)
        if pin == ADMIN_PIN:
            # Store the admin PIN in the session to remember admin access
            request.session['is_admin'] = True
            return redirect('adminconsole')
        else:
            return HttpResponse("Incorrect PIN. Access denied.")
    return render(request, 'enter_admin_pin.html')


def admin_console(request):
    # Get the directory path from the query parameters
    path = request.GET.get('path', '')
    full_path = os.path.normpath(os.path.join(
        settings.BASE_DIR, path))  # Normalize full path

    # Check if the path exists
    if not os.path.exists(full_path):
        raise Http404("Directory does not exist")

    items = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        relative_path = os.path.relpath(item_path, settings.BASE_DIR)
        is_dir = os.path.isdir(item_path)

        # Check if the directory is public by checking if it's in the Directory table
        is_public = Directory.objects.filter(path=item_path).exists()

        # print(f"relative_path - {relative_path.encode('utf-8', 'replace')}")
        # print(f"full_path - {item_path}")

        item_info = {
            'name': item,
            'relative_path': relative_path,
            'is_dir': is_dir,
            'size': os.path.getsize(item_path) if not is_dir else None,
            'modified': datetime.datetime.fromtimestamp(os.path.getmtime(item_path)),
            'is_public': is_public  # True if the directory is public
        }
        items.append(item_info)

    context = {
        'items': items,
        'current_path': path,  # Pass the current path for breadcrumb navigation
    }
    return render(request, 'adminconsole.html', context)


def toggle_visibility(request):
    if request.method == 'POST':
        path = request.POST.get('path')
        full_path = os.path.normpath(os.path.join(
            settings.BASE_DIR, path))  # Normalize the path
        current_path = request.POST.get('current_path')
        # Check if "children" is included
        include_children = request.POST.get('include_children') == 'true'

        print(f"path of private file to be added = {full_path}")

        # Check if the directory is already public (exists in Directory table)
        directory = Directory.objects.filter(path=full_path).first()

        if directory:
            # If it's public, remove it (and optionally, all subdirectories) from the Directory table (set to private)
            print("Setting directory to private")
            if include_children:
                print("Setting all subdirectories to private")
                Directory.objects.filter(path__startswith=full_path).delete()
            else:
                directory.delete()
        else:
            # If it's private, add it (and optionally, all subdirectories) to the Directory table (set to public)
            print("Setting directory to public")
            # Create entry for main directory
            Directory.objects.create(path=full_path)

            if include_children:
                print("Setting all subdirectories to public")
                for root, dirs, _ in os.walk(path):
                    for sub_dir in dirs:
                        sub_dir_path = os.path.join(root, sub_dir)
                        # normalized_sub_dir_path = os.path.relpath(
                        #     sub_dir_path, BASE_DIR)
                        # print(sub_dir_path)
                        Directory.objects.create(path=sub_dir_path)

    # Redirect back to the current directory in the admin console
    return redirect(f'/serveradmin/?path={current_path}')

    # Redirect back to the current directory in the admin console
    return redirect(f'/serveradmin/?path={current_path}')

# react stuff


# def theatre_view(request):
#     search_query = request.GET.get('q', '')

#     if search_query:
#         # Filter movies by search query
#         movies = Movie.objects.filter(movie_name__icontains=search_query)
#     else:
#         # Show all movies
#         movies = Movie.objects.all()

#     return render(request, 'theatre.html', {'movies': movies})


def index(request):
    return render(request, 'frontend/build/index.html')


def video_list(request):
    print("WORKING")
    try:
        search_query = request.GET.get('q', '')
        fields = ['id', 'file_name', 'movie_name', 'file_path',
                  'length', 'added_to_favorites', 'last_position']

        # Get all public directories from the Directory model and normalize paths
        public_dirs = Directory.objects.values_list('path', flat=True)
        public_dirs = [str(Path(path).resolve())
                       for path in public_dirs]  # Normalize with Path.resolve()

        # Log the list of normalized public directories
        print("Normalized public directories:", public_dirs)

        # Filter for movies that have public directories in their path
        movies = Movie.objects.all().values(*fields)
        accessible_movies = []

        for movie in movies:
            # Normalize movie path
            movie_path = Path(movie['file_path']).resolve()
            is_accessible = False

            # Check each parent directory of the movie file path
            for parent in movie_path.parents:
                if str(parent) in public_dirs:
                    is_accessible = True
                    break

            # Add movie to accessible list if it has a public directory in its path
            if is_accessible:
                movie['relative_path'] = movie_path.as_posix().replace('D:/', '')
                accessible_movies.append(movie)

        # Filter movies by search query if provided
        if search_query:
            accessible_movies = [movie for movie in accessible_movies if search_query.lower(
            ) in movie['movie_name'].lower()]

        return JsonResponse(accessible_movies, safe=False)
    except Exception as e:
        logger.error(f"Error in video_list: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def category_list(request):
    categories = FileTypeCategory.objects.all()
    return render(request, 'serveradmin/category_list.html', {'categories': categories})


def category_create(request):
    if request.method == 'POST':
        form = FileTypeCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = FileTypeCategoryForm()
    return render(request, 'serveradmin/category_form.html', {'form': form})


def category_edit(request, pk):
    category = get_object_or_404(FileTypeCategory, pk=pk)
    if request.method == 'POST':
        form = FileTypeCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = FileTypeCategoryForm(instance=category)
    return render(request, 'serveradmin/category_form.html', {'form': form})


def category_delete(request, pk):
    category = get_object_or_404(FileTypeCategory, pk=pk)
    if request.method == 'POST':
        category.delete()
        return redirect('category_list')
    return render(request, 'serveradmin/category_confirm_delete.html', {'category': category})
