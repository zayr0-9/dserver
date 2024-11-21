from django.http import JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect, StreamingHttpResponse, FileResponse, JsonResponse
import os
import datetime
import shutil
import re
import mimetypes
import hashlib
import subprocess
import requests
import json
from PIL import Image
from django.utils.http import http_date
from moviepy.editor import VideoFileClip
from urllib.parse import quote
from transfer.models import FileSearchMetadata, Movie
from django.db.models import Q
from .models import Directory, Movie
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
import logging
from pathlib import Path
from urllib.parse import unquote, quote
import string
from ctypes import windll
from django.conf import settings
from .models import FileTypeCategory
from .forms import FileTypeCategoryForm


# logger = logging.getLogger(__name__)


# BASE_DIR = 'C:\\'  # Change this to the base directory you want to start with
ADMIN_PIN = "12345"


def file_upload(request):
    # upload_dir = os.path.join(BASE_DIR, 'uploads')
    # os.makedirs(upload_dir, exist_ok=True)
    base_dir = request.GET.get('base_dir')
    relative_path = request.GET.get('path', ' ').lstrip('/\\')

    if base_dir and relative_path:
        upload_dir = os.path.join(f"{base_dir}:/", relative_path)
    else:
        upload_dir = os.path.join(settings.BASE_DIR, 'uploads')

    os.makedirs(upload_dir, exist_ok=True)

    if request.method == 'POST' and request.FILES.getlist('files'):
        uploaded_files = request.FILES.getlist('files')
        uploaded_file_paths = []
        thumbnails = []

        for uploaded_file in uploaded_files:
            file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Process video files for thumbnails
            if uploaded_file.name.lower().endswith(('.mp4', '.avi', '.mov', '.webm', '.mkv')):
                clip = None
                try:
                    clip = VideoFileClip(file_path)
                    frame = clip.get_frame(t=1)  # Get frame at 1 second
                    img = Image.fromarray(frame)
                    img.thumbnail((100, 100))
                    thumbnail_path = os.path.join(
                        upload_dir, f'thumb_{uploaded_file.name}.jpg')
                    img.save(thumbnail_path, 'JPEG')
                    thumbnails.append(os.path.basename(thumbnail_path))
                except Exception as e:
                    print(f"Error processing video {uploaded_file.name}: {e}")
                finally:
                    if clip:
                        clip.reader.close()  # Ensure the video reader is closed
                        clip.close()  # Close the video clip explicitly

            uploaded_file_paths.append(file_path)

        # Send notification to Node.js server
        try:
            response = requests.post('http://localhost:3000/upload-success',
                                     data=json.dumps(
                                         {'message': 'File upload successful!'}),
                                     headers={'Content-Type': 'application/json'})
        except requests.ConnectionError as e:
            print(f"Node.js server connection failed: {e}")

        # Return the list of uploaded file paths and thumbnails
        return render(request, 'upload.html', {
            'file_paths': uploaded_file_paths,
            'thumbnails': thumbnails,
            'base_dir': base_dir,
            'current_path': relative_path
        })

    return render(request, 'upload.html', {
        'base_dir': base_dir,
        'current_path': relative_path
    })


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


def file_list(request, base_dir='', path=''):
    base_dir = unquote(base_dir)
    path = unquote(path).lstrip('/\\')

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

    # Define file type extensions
    FILE_TYPES = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
        'videos': ['.mp4', '.avi', '.mov', '.webm', '.mkv'],
        'documents': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'],
        'audio': ['.mp3', '.wav', '.aac', '.flac'],
        'archives': ['.zip', '.rar', '.7z', '.tar', '.gz']
    }

    if not base_dir:
        return redirect('drives')

    base_dir_with_drive = f"{base_dir}:\\"
    full_path = os.path.normpath(os.path.join(base_dir_with_drive, path))

    if not os.path.exists(full_path):
        raise Http404("Directory does not exist")

    if not full_path.startswith(os.path.normpath(base_dir)):
        raise Http404("Access denied")

    # Check if the directory is private
    directory_entry = Directory.objects.filter(path=full_path).first()
    session_key = f"admin_pin_valid_{base_dir}_{path}"

    if not directory_entry and not request.session.get(session_key, False):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
            entered_pin = request.POST.get('pin', None)
            if entered_pin == ADMIN_PIN:
                request.session[session_key] = True
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Incorrect PIN. Please try again.'})

        return render(request, 'file_list.html', {
            'items': [],
            'current_path': path,
            'base_dir': base_dir,
            'thumbnail_size': 500,
            'is_private': True,
            'q': request.GET.get('q', '')
        })

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
            stat = entry.stat(follow_symlinks=False)
            size = stat.st_size if not is_dir else None
            modified = datetime.datetime.fromtimestamp(stat.st_mtime)
            created = datetime.datetime.fromtimestamp(stat.st_ctime)
            relative_path = os.path.join(path, item_name)
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
                'is_video': is_video
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
                        image = Image.open(item_path)
                        image.thumbnail((thumbnail_size, thumbnail_size))
                        thumbnail_format = 'PNG' if image.mode == 'RGBA' else 'JPEG'
                        image.save(thumbnail_path, thumbnail_format)

                    item_info['thumbnail'] = thumbnail_filename
                except Exception as e:
                    print(f"Failed to create thumbnail for {item_name}: {e}")

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
                    print(
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
            if item['modified'] < date_from_dt:
                continue
        if date_to:
            date_to_dt = datetime.datetime.strptime(date_to, '%Y-%m-%d')
            if item['modified'] > date_to_dt:
                continue

        filtered_items.append(item)

    # Apply sorting
    reverse = (sort_dir == 'desc')

    # Define sort key function
    def sort_key(item):
        # Use empty string if sort_by key is None
        return item.get(sort_by) or ''

    # Ensure directories are listed first
    filtered_items.sort(
        key=lambda item: (not item['is_dir'], sort_key(item)),
        reverse=reverse
    )

    context = {
        'items': filtered_items,
        'current_path': path,
        'base_dir': base_dir,
        'thumbnail_size': thumbnail_size,
        'is_private': False,
        'q': request.GET.get('q', ''),
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'filter_type': filter_type,
        'file_type': sub_file_type,
        'size_min': size_min,
        'size_max': size_max,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(request, 'file_list.html', context)


def file_list_api(request, drive_letter):
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

    # Define file type extensions
    FILE_TYPES = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
        'videos': ['.mp4', '.avi', '.mov', '.webm', '.mkv'],
        'documents': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'],
        'audio': ['.mp3', '.wav', '.aac', '.flac'],
        'archives': ['.zip', '.rar', '.7z', '.tar', '.gz']
    }

    if not base_dir:
        return redirect('drives')

    base_dir_with_drive = f"{base_dir}:\\"
    full_path = os.path.normpath(os.path.join(base_dir_with_drive, path))

    if not os.path.exists(full_path):
        raise Http404("Directory does not exist")

    if not full_path.startswith(os.path.normpath(base_dir)):
        raise Http404("Access denied")

    # Check if the directory is private
    directory_entry = Directory.objects.filter(path=full_path).first()
    session_key = f"admin_pin_valid_{base_dir}_{path}"

    if not directory_entry and not request.session.get(session_key, False):
        if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            entered_pin = request.POST.get('pin', None)
            if entered_pin == ADMIN_PIN:
                request.session[session_key] = True
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Incorrect PIN. Please try again.'}, status=401)
        else:
            # Return JSON indicating the directory is private
            return JsonResponse({'is_private': True}, status=401)

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
            stat = entry.stat(follow_symlinks=False)
            size = stat.st_size if not is_dir else None
            modified = datetime.datetime.fromtimestamp(stat.st_mtime)
            created = datetime.datetime.fromtimestamp(stat.st_ctime)
            relative_path = os.path.join(path, item_name)
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
                'is_video': is_video
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
                        image = Image.open(item_path)
                        image.thumbnail((thumbnail_size, thumbnail_size))
                        thumbnail_format = 'PNG' if image.mode == 'RGBA' else 'JPEG'
                        image.save(thumbnail_path, thumbnail_format)

                    item_info['thumbnail'] = thumbnail_filename
                except Exception as e:
                    print(f"Failed to create thumbnail for {item_name}: {e}")

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
                    print(
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
            if item['modified'] < date_from_dt:
                continue
        if date_to:
            date_to_dt = datetime.datetime.strptime(date_to, '%Y-%m-%d')
            if item['modified'] > date_to_dt:
                continue

        filtered_items.append(item)

    # Apply sorting
    reverse = (sort_dir == 'desc')

    # Define sort key function
    def sort_key(item):
        # Use empty string if sort_by key is None
        return item.get(sort_by) or ''

    # Ensure directories are listed first
    filtered_items.sort(
        key=lambda item: (not item['is_dir'], sort_key(item)),
        reverse=reverse
    )

    response_data = {
        'items': filtered_items,  # or 'filtered_items' after filtering
        'current_path': path,
        'base_dir': base_dir,
        'thumbnail_size': thumbnail_size,
        'is_private': False,
        'q': request.GET.get('q', ''),
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'filter_type': filter_type,
        'file_type': sub_file_type,
        'size_min': size_min,
        'size_max': size_max,
        'date_from': date_from,
        'date_to': date_to,
    }
    return JsonResponse(response_data)  # json for react api


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
    relative_path = request.GET.get('path', '')
    base_dir = settings.BASE_DIR
    full_path = os.path.normpath(os.path.join(base_dir, relative_path))

    # Prevent directory traversal attacks
    if not full_path.startswith(str(base_dir)):
        raise Http404("Invalid path")

    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        raise Http404("Directory does not exist")

    dir_name = os.path.basename(os.path.normpath(full_path))
    zip_filename = f"{dir_name}.zip"
    zip_dir = os.path.join(base_dir, 'temparchive')
    os.makedirs(zip_dir, exist_ok=True)
    zip_path = os.path.join(zip_dir, zip_filename)

    # Determine whether to create or reuse the zip file
    regenerate_zip = False

    if os.path.exists(zip_path):
        # Get the modification time of the zip file
        zip_mtime = os.path.getmtime(zip_path)

        # Get the latest modification time in the directory
        dir_mtime = get_latest_mtime(full_path)

        if dir_mtime > zip_mtime:
            regenerate_zip = True
    else:
        regenerate_zip = True

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


def video_stream_page(request, path, filename):
    file_path = os.path.join(BASE_DIR, path, filename)
    if not os.path.exists(file_path):
        raise Http404("File does not exist")
    context = {
        'video_path': file_path,
        'video_filename': filename,
    }
    return render(request, 'video_stream.html', context)


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
