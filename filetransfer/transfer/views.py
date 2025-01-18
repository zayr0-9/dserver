
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
from .models import FileMetadata
from rapidfuzz import process, fuzz, utils
from concurrent.futures import ThreadPoolExecutor


# logger = logging.getLogger(__name__)


# BASE_DIR = 'C:\\'  # Change this to the base directory you want to start with
ADMIN_PIN = "12345"


logger = logging.getLogger(__name__)
FILE_TYPES = {
    'images': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff'],
    'videos': ['.mp4', '.avi', '.mov', '.webm', '.mkv', '.gif'],
    'documents': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.log', '.txt', '.py', '.js', '.html', '.css',
                       '.json', '.md', '.java', '.c', '.cpp'],
    'audio': ['.mp3', '.wav', '.aac', '.flac'],
    'archives': ['.zip', '.rar', '.7z', '.tar', '.gz']
}
temp_dir = os.path.join(settings.BASE_DIR, 'temp_thumbnails')

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
    """
    Handle file search requests.
    Query parameter: ?q=search_term
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': [], 'message': 'No query provided.'}, status=200)

    # Example: search by name or relative_path
    matches = FileMetadata.objects.filter(
        Q(name__icontains=query) | Q(relative_path__icontains=query)
    )

    # Optional: apply additional filters or constraints here (e.g., file size, file_type, etc.)

    # Serialize the results
    results = []
    for item in matches:
        results.append({
            'name': item.name,
            'relative_path': item.relative_path,
            'absolute_path': item.absolute_path,
            'drive': item.absolute_path[:3],
            'is_dir': item.is_dir,
            'size': item.size,
            'modified': item.modified.strftime('%Y-%m-%d %H:%M:%S'),
            'created': item.created.strftime('%Y-%m-%d %H:%M:%S'),
            'file_type': item.file_type.name if item.file_type else None,
        })

    return JsonResponse({'results': results}, status=200)

# def fuzzy_search_files(request):
#     """
#     Fuzzy search in FileMetadata using RapidFuzz's WRatio scorer.
#     Query parameter: ?q=search_term
#     """
#     query = request.GET.get('q', '')
#     if not isinstance(query, str):
#         query = str(query)
#     query = query.strip()

#     if not query:
#         return JsonResponse({'results': [], 'message': 'No query provided.'}, status=200)

#     # 1) Load records from DB
#     all_files = FileMetadata.objects.all()

#     # 2) Build `choices`. Convert any non-string fields to string.
#     choices = []
#     for item in all_files:
#         # Safely coerce to string
#         name_str = str(item.name) if item.name else ""
#         relative_str = str(item.relative_path) if item.relative_path else ""

#         # Combine them for searching
#         search_key = f"{name_str} {relative_str}"
#         # store (search_key, item)
#         choices.append((search_key, item))

#     # 3) Use process.extract
#     #    If any entry in `choices` is not a string, or if `search_key` includes non-string values,
#     #    forcing them to string above should fix it.
#     results_fuzzy = process.extract(
#         query,
#         choices,
#         scorer=fuzz.WRatio,  # or fuzz.partial_ratio
#         limit=20,
#         processor=utils.default_process  # for auto-lowercase/trimming
#     )

#     final_results = []
#     for matched_string, score, item_obj in results_fuzzy:
#         # If score is too low, skip
#         if score < 50:
#             continue

#         final_results.append({
#             'name': item_obj.name,
#             'relative_path': item_obj.relative_path,
#             'absolute_path': item_obj.absolute_path,
#             'is_dir': item_obj.is_dir,
#             'size': item_obj.size,
#             'modified': item_obj.modified.strftime('%Y-%m-%d %H:%M:%S'),
#             'created': item_obj.created.strftime('%Y-%m-%d %H:%M:%S'),
#             'file_type': item_obj.file_type.name if item_obj.file_type else None,
#             'score': score,  # optionally return the fuzzy match score
#         })

#     return JsonResponse({'results': final_results}, status=200)
# need to fix 

def drives(request):
    drives = get_drives()
    context = {
        'drives': drives,
    }
    return render(request, 'drivelist.html', context)




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
    print("Fetching drives")
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    
    # Drive types constants
    DRIVE_UNKNOWN = 0
    DRIVE_NO_ROOT_DIR = 1
    DRIVE_REMOVABLE = 2
    DRIVE_FIXED = 3
    DRIVE_REMOTE = 4
    DRIVE_CDROM = 5
    DRIVE_RAMDISK = 6

    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drive_path = f"{letter}:/"
            drive_type = windll.kernel32.GetDriveTypeW(drive_path)
            # Include only fixed drives (e.g., hard disks, SSDs)
            if drive_type == DRIVE_FIXED:
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
    return os.path.splitext(file_path)[1].lower() in FILE_TYPES['documents']


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


def get_request_params(request):
    return {
        'path': unquote(request.GET.get('path', '')).lstrip('/\\'),
        'sort_by': request.GET.get('sort_by', 'name'),
        'sort_dir': request.GET.get('sort_dir', 'asc'),
        'filter_type': request.GET.get('type', 'all'),
        'size_min': request.GET.get('size_min'),
        'size_max': request.GET.get('size_max'),
        'date_from': request.GET.get('date_from'),
        'date_to': request.GET.get('date_to'),
        'file_type': request.GET.get('file_type', 'all'),
        'page': max(1, int(request.GET.get('page', '1'))),
        'page_size': int(request.GET.get('page_size', '100')),
        'show_hidden_files': False
    }

def get_directory_items(full_path, show_hidden_files, path):
    items = []
    with os.scandir(full_path) as entries:
        for entry in entries:
            if not show_hidden_files and entry.name.startswith('.'):
                continue
            try:
                stat = entry.stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            relative_path = os.path.join(path, entry.name).replace('\\', '/')
            file_ext = os.path.splitext(entry.name)[1].lower()
            if file_ext in FILE_TYPES['videos']:
                is_video = True
            else:
                is_video=False
            if file_ext in FILE_TYPES['documents']:
                is_text_file = True
            else: 
                is_text_file = False

            items.append({
                'name': entry.name,
                'path': path,
                'is_dir': entry.is_dir(follow_symlinks=False),
                'size': stat.st_size if not entry.is_dir() else None,
                'modified': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'relative_path': relative_path,
                'thumb_path': entry.path,
                'is_video': is_video,
                'is_text' : is_text_file
            })
    return items

def generate_thumbnail(item):
    # Thumbnail generation logic for images and videos
    thumbnail_size = 100
    os.makedirs(temp_dir, exist_ok=True)
    file_ext = os.path.splitext(item['name'])[1].lower()

    try:
        file_identifier = f"{item['thumb_path']}_{thumbnail_size}"
        thumbnail_hash = hashlib.md5(file_identifier.encode('utf-8')).hexdigest()
        thumbnail_ext = '.png' if file_ext == '.png' else '.jpg'
        thumbnail_filename = f"thumb_{thumbnail_hash}{thumbnail_ext}"
        thumbnail_path = os.path.join(temp_dir, thumbnail_filename)

        if not item['is_dir'] and file_ext in FILE_TYPES['images']:
            # Thumbnail generation for images
            if os.path.exists(thumbnail_path):
                item['thumbnail'] = thumbnail_filename  # Skip generation
                return
            #generate thumbnail for image
            with Image.open(item['thumb_path']) as image:
                image.thumbnail((thumbnail_size, thumbnail_size))
                image_format = 'PNG' if image.mode == 'RGBA' else 'JPEG'
                image.save(thumbnail_path, image_format)

            item['thumbnail'] = thumbnail_filename

        elif not item['is_dir'] and file_ext in FILE_TYPES['videos']:
            if os.path.exists(thumbnail_path):
                item['thumbnail'] = thumbnail_filename  # Set generated thumbnail
                return
            # Thumbnail generation for videos
            generate_video_thumbnail(item)

    except Exception as e:
        logger.error(f"Failed to create thumbnail for {item['name']}: {e}")

def get_ffmpeg_hwaccels():
    """
    Returns a list of hardware accelerations supported by the local FFmpeg build.
    For example: ['cuda', 'dxva2', 'vaapi', 'qsv', 'vdpau', 'videotoolbox', ...]
    """
    try:
        command = ['ffmpeg', '-hwaccels']
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        # The first line is typically "Hardware acceleration methods:"
        # Subsequent lines are the available hwaccels
        lines = result.stdout.strip().split('\n')
        hwaccels = [line.strip() for line in lines[1:] if line.strip()]
        return hwaccels
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to query FFmpeg hardware accelerations: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching FFmpeg hardware accelerations: {e}")
        return []

def choose_hwaccel_method(preferred_order=None):
    """
    Return the first available hardware acceleration method based on a preferred
    order, or None if none is available.
    
    Example usage:
      hwaccel = choose_hwaccel_method(['cuda', 'vaapi', 'qsv', 'dxva2', 'videotoolbox'])
      if hwaccel:
          # build ffmpeg command with hwaccel
      else:
          # fallback to software
    """
    hwaccels = get_ffmpeg_hwaccels()
    # logger.info(f"Detected FFmpeg hardware accelerations: {hwaccels}")

    if not hwaccels:
        return None

    # If the caller didn't specify a preferred order, let's define a generic default
    if preferred_order is None:
        # Common possibilities: 'cuda' (NVIDIA), 'vaapi' (Intel/Linux), 'qsv' (Intel Quick Sync), 
        # 'videotoolbox' (macOS), 'dxva2' (Windows), 'vdpau' (older Linux)
        preferred_order = ['cuda', 'vaapi', 'qsv', 'videotoolbox', 'dxva2', 'vdpau']

    for hw in preferred_order:
        if hw in hwaccels:
            # logger.info(f"Using hardware acceleration: {hw}")
            return hw

    # logger.info("No preferred hardware acceleration found. Falling back to software.")
    return None

def generate_video_thumbnail(item, thumbnail_size=100):
    file_identifier = f"{item['thumb_path']}_{thumbnail_size}"
    thumbnail_hash = hashlib.md5(file_identifier.encode('utf-8')).hexdigest()
    thumbnail_filename = f"thumb_{thumbnail_hash}.jpg"
    thumbnail_path = os.path.join(temp_dir, thumbnail_filename)

    if os.path.exists(thumbnail_path):
        item['thumbnail'] = thumbnail_filename  # Skip generation
        return

    # Choose the hardware acceleration method if available
    hwaccel_method = choose_hwaccel_method()
    
    # Base command (shared arguments)
    base_args = [
        'ffmpeg',
        '-y',             # Overwrite output if exists
        '-i', item['thumb_path'],  # Input video file
        '-ss', '00:00:10',         # Timestamp to grab frame
        '-vframes', '1',           # Extract one frame
        '-vf',  f'scale=-1:{thumbnail_size}',  # Resize
        thumbnail_path
    ]

    if hwaccel_method:
        # Insert -hwaccel <method> right after the 'ffmpeg' and '-y'
        hwaccel_args = base_args[:2] + ['-hwaccel', hwaccel_method] + base_args[2:]
    else:
        # No hardware acceleration; just use base_args
        hwaccel_args = base_args

    # 1) Try hardware (or direct) command
    try:
        result = subprocess.run(hwaccel_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            # logger.warning(f"Hardware-accelerated FFmpeg call failed with code {result.returncode}. Falling back to software.")
            # 2) Fallback to software-only if we tried hardware
            if hwaccel_method:
                # Re-run base_args without hwaccel in case that's the problem
                sw_result = subprocess.run(base_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                if sw_result.returncode != 0:
                    logger.error(f"Software fallback also failed with code {sw_result.returncode}")
                    return
        # If no hardware method was chosen, we already used base_args

    except Exception as e:
        # logger.warning(f"Exception while running FFmpeg with hardware accel: {e}. Falling back to software.")
        sw_result = subprocess.run(base_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if sw_result.returncode != 0:
            logger.error(f"Software fallback also failed with code {sw_result.returncode}")
            return

    # Finally, if the thumbnail was created, update item
    if os.path.exists(thumbnail_path):
        item['thumbnail'] = thumbnail_filename

def process_thumbnails(items):
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(generate_thumbnail, items)
    except Exception as e:
        logger.error(f"Error during thumbnail generation: {e}")


def filter_items(items, params):
    # Apply filtering logic
    # Apply filtering
    filtered_items = []
    for item in items:
        # Apply sub-file type filter first
        if params['file_type'] != 'all' and not item['is_dir']:
            file_ext = os.path.splitext(item['name'])[1].lower()
            if file_ext not in FILE_TYPES.get(params['file_type'], []):
                continue  # Skip files that don't match the selected sub-type

        # Then filter by type (dir, file, all)
        if params['filter_type'] == 'dir' and not item['is_dir']:
            continue
        if params['filter_type'] == 'file' and item['is_dir']:
            continue

        # Filter by size
        if params['size_min'] and item['size'] is not None and item['size'] < int(params['size_min']):
            continue
        if params['size_max'] and item['size'] is not None and item['size'] > int(params['size_max']):
            continue

        # Filter by date
        if params['date_from']:
            date_from_dt = datetime.datetime.strptime(params['date_from'], '%Y-%m-%d')
            item_modified_dt = datetime.datetime.fromisoformat(
                item['modified'])
            if item_modified_dt < date_from_dt:
                continue
        if params['date_to']:
            date_to_dt = datetime.datetime.strptime(params['date_to'], '%Y-%m-%d')
            item_modified_dt = datetime.datetime.fromisoformat(
                item['modified'])
            if item_modified_dt > date_to_dt:
                continue
        filtered_items.append(item)
    return(filtered_items)  # Implement filters for type, size, and dates

def sort_items(items, sort_by, sort_dir):
    # Sort items by key and order
    reverse = (sort_dir == 'desc')
    return sorted(items, key=lambda x: x.get(sort_by, ""), reverse=reverse)

def paginate_items(items, page, page_size):
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    return items[start_index:end_index], len(items)

def file_list_api(request, drive_letter):
    base_dir = unquote(drive_letter)
    if not base_dir:
        return JsonResponse({'error': 'Base directory not specified'}, status=400)
    
    params = get_request_params(request)
    full_path = os.path.normpath(os.path.join(f"{base_dir}:\\", params['path']))

    if not os.path.exists(full_path):
        raise Http404("Directory does not exist")

    if not full_path.startswith(os.path.normpath(f"{base_dir}:\\")):
        raise Http404("Access denied")

    items = get_directory_items(full_path, params['show_hidden_files'], params['path'])
    process_thumbnails(items)
    filtered_items = filter_items(items, params)
    sorted_items = sort_items(filtered_items, params['sort_by'], params['sort_dir'])
    paginated_items, total_items = paginate_items(sorted_items, params['page'], params['page_size'])

    return JsonResponse({
        'items': sorted_items,
        'pagination': {
            'current_page': params['page'],
            'page_size': params['page_size'],
            'total_items': total_items
        }
    })


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

def admin_console_api(request):
    path = request.GET.get('path', '')
    full_path = os.path.normpath(os.path.join(settings.BASE_DIR, path))
    
    if not os.path.exists(full_path):
        return JsonResponse({'error': 'Directory does not exist'}, status=404)
    
    items = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        relative_path = os.path.relpath(item_path, settings.BASE_DIR)
        is_dir = os.path.isdir(item_path)
        is_public = Directory.objects.filter(path=item_path).exists()
        
        item_info = {
            'name': item,
            'relative_path': relative_path,
            'is_dir': is_dir,
            'size': os.path.getsize(item_path) if not is_dir else None,
            'modified': datetime.datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat(),
            'is_public': is_public
        }
        items.append(item_info)
    
    return JsonResponse({'items': items, 'current_path': path})

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

SETUP_JSON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../setup.json")
)

@csrf_exempt  # Allow this endpoint to be called without CSRF token for simplicity (adjust for production)
def update_drive_letter(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method. Use POST."}, status=405)

    try:
        data = json.loads(request.body)
        new_drive_letter = data.get("drive_letter", "").strip().upper()

        if not new_drive_letter or len(new_drive_letter) != 1 or not new_drive_letter.isalpha():
            return JsonResponse({"error": "Invalid drive letter. Provide a single letter (e.g., 'C')."}, status=400)

        # Load the current setup.json
        with open(SETUP_JSON_PATH, "r") as file:
            setup_data = json.load(file)

        # Update the drive_letter
        setup_data["drive_letter"] = new_drive_letter

        # Write back to setup.json
        with open(SETUP_JSON_PATH, "w") as file:
            json.dump(setup_data, file, indent=2)

        return JsonResponse({"message": "Drive letter updated successfully.", "drive_letter": new_drive_letter})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON input."}, status=400)
    except FileNotFoundError:
        return JsonResponse({"error": "setup.json file not found."}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

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
