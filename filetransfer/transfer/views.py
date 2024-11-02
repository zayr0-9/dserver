from django.http import JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect, StreamingHttpResponse, FileResponse, JsonResponse
import os
import datetime
import shutil
import re
import mimetypes
import subprocess
import requests
import json
from PIL import Image
from django.utils.http import http_date
from moviepy.editor import VideoFileClip
from urllib.parse import quote
from transfer.models import FileMetadata, Movie
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

# logger = logging.getLogger(__name__)


BASE_DIR = 'C:\\'  # Change this to the base directory you want to start with
ADMIN_PIN = "1234"


def file_upload(request):
    upload_dir = os.path.join(BASE_DIR, 'uploads')
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
            'thumbnails': thumbnails
        })

    return render(request, 'upload.html')


def search_files(request):
    search_query = request.GET.get('q', '').strip()  # Get search query
    results = []

    if search_query:
        # Perform a search using ORM with case-insensitive matching
        results = FileMetadata.objects.filter(
            Q(file_name__icontains=search_query) |
            Q(file_path__icontains=search_query)
        )

    return render(request, 'search_results.html', {'results': results, 'query': search_query})


def search_files(request):
    # Get the search query from the request
    query = request.GET.get('q', '').strip()
    thumbnail_size = int(request.GET.get('thumbnail_size', 100))

    # Debug output to see the query and what's being searched
    print(f"Search query: {query}")

    if query:
        # Perform case-insensitive search for both file names and file paths
        results = FileMetadata.objects.filter(
            Q(file_name__icontains=query) | Q(file_path__icontains=query)
        )
    else:
        # No search results if no query is provided
        results = FileMetadata.objects.none()

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

    if not base_dir:
        return redirect('drives')

    base_dir_with_drive = f"{base_dir}:\\"

    full_path = os.path.normpath(os.path.join(base_dir_with_drive, path))
    print(f"Base dir: {base_dir}")
    print(f"Base dir with drive: {base_dir_with_drive}")
    print(f"Path: {path}")
    print(f"Full path to find = {full_path}")

    # Ensure the path exists and is within the base_dir
    if not os.path.exists(full_path):
        raise Http404("Directory does not exist")

    if not full_path.startswith(os.path.normpath(base_dir)):
        raise Http404("Access denied")

    # Check if the directory is not in the Directory model (indicating it's private)
    directory_entry = Directory.objects.filter(path=full_path).first()

    # If the directory is private (not in the Directory model), ask for admin PIN
    if not directory_entry and not request.session.get(f'admin_pin_valid_{path}', False):
        print("Private directory asking for PIN\n")
        if request.method == 'POST':
            # Handle PIN submission
            entered_pin = request.POST.get('pin', None)
            if entered_pin == ADMIN_PIN:
                # Save the valid PIN in the session
                request.session[f'admin_pin_valid_{path}'] = True
            else:
                return render(request, 'file_list.html', {
                    'items': [],
                    'current_path': path,
                    'base_dir': base_dir,
                    'thumbnail_size': 100,
                    'is_private': True,
                    'pin_error': 'Incorrect PIN. Please try again.',
                    'q': request.GET.get('q', '')
                })

        # Show the PIN entry popup if the PIN is not already submitted
        return render(request, 'file_list.html', {
            'items': [],
            'current_path': path,
            'base_dir': base_dir,
            'thumbnail_size': 100,
            'is_private': True,
            'q': request.GET.get('q', '')
        })

    # Default size is 100x100 for thumbnails
    thumbnail_size = int(request.GET.get('thumbnail_size', 100))

    # Temporary thumbnail directory
    temp_dir = os.path.join(settings.BASE_DIR, 'temp_thumbnails')
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)

    video_extensions = ('.mp4', '.avi', '.mov', '.webm', '.mkv')

    items = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        is_video = not os.path.isdir(
            item_path) and item.lower().endswith(video_extensions)
        relative_path = os.path.join(path, item)
        item_info = {
            'name': item,
            'path': path,
            'relative_path': relative_path,
            'is_dir': os.path.isdir(item_path),
            'size': os.path.getsize(item_path) if os.path.isfile(item_path) else None,
            'modified': datetime.datetime.fromtimestamp(os.path.getmtime(item_path)),
            'thumbnail': None,
            'is_video': is_video
        }

        if not item_info['is_dir']:
            ext = os.path.splitext(item)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                try:
                    image = Image.open(item_path)
                    image.thumbnail((thumbnail_size, thumbnail_size))

                    if image.mode == 'RGBA':
                        thumbnail_format = 'PNG'
                        thumbnail_ext = '.png'
                    else:
                        thumbnail_format = 'JPEG'
                        thumbnail_ext = '.jpg'

                    base_name, ext = os.path.splitext(os.path.basename(item))
                    thumbnail_filename = f"thumb_{base_name}{thumbnail_ext}"
                    thumbnail_path = os.path.join(temp_dir, thumbnail_filename)
                    image.save(thumbnail_path, thumbnail_format)
                    item_info['thumbnail'] = thumbnail_filename
                except Exception as e:
                    print(f"Failed to create thumbnail for {item}: {e}")

        items.append(item_info)

    context = {
        'items': items,
        'current_path': path,
        'base_dir': base_dir,
        'thumbnail_size': thumbnail_size,
        'is_private': False,  # Directory is not private if it reached here
        'q': request.GET.get('q', '')
    }
    return render(request, 'file_list.html', context)


def download_zip(request):
    relative_path = request.GET.get('path', '')
    base_dir = BASE_DIR
    full_path = os.path.normpath(os.path.join(base_dir, relative_path))

    # Prevent directory traversal attacks
    if not full_path.startswith(base_dir):
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
            subprocess.check_call(['7z', 'a', '-tzip', zip_path, full_path])
        except subprocess.CalledProcessError:
            return HttpResponse("Error creating zip file.", status=500)

    # Construct the URL that Nginx will serve
    zip_url = f"/temparchive/{quote(zip_filename)}"

    # Redirect the user to the zip file URL for Nginx to handle byte-range requests
    return HttpResponseRedirect(zip_url)


def get_latest_mtime(directory):
    latest_mtime = 0
    for root, dirs, files in os.walk(directory):
        for fname in files:
            fpath = os.path.join(root, fname)
            mtime = os.path.getmtime(fpath)
            if mtime > latest_mtime:
                latest_mtime = mtime
    return latest_mtime


def download_file(request, path, filename):
    file_path = os.path.join(BASE_DIR, path, filename)
    if not os.path.exists(file_path):
        raise Http404("File does not exist")
    # Open the file for streaming the response
    response = FileResponse(open(file_path, 'rb'),
                            as_attachment=True, filename=filename)
    response['Content-Type'] = 'application/octet-stream'
    # Indicate that the server accepts byte-range requests
    response['Accept-Ranges'] = 'bytes'
    return response


def stream_video(request, path, filename):
    file_path = path
    if not os.path.exists(file_path):
        raise Http404("File does not exist")

    # Get the file size and content type
    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)

    # Determine the range request
    range_header = request.headers.get('Range', '').strip()
    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    if range_match:
        start = int(range_match.group(1))
        end = range_match.group(2)
        end = int(end) if end else file_size - 1
    else:
        start = 0
        end = file_size - 1

    # Calculate the content length and the actual start and end of the content to serve
    content_length = (end - start) + 1

    # Create a generator to stream the file in chunks
    def file_stream(file, start, end, chunk_size=8192):
        file.seek(start)
        remaining_bytes = (end - start) + 1
        while remaining_bytes > 0:
            chunk = file.read(min(chunk_size, remaining_bytes))
            if not chunk:
                break
            remaining_bytes -= len(chunk)
            yield chunk

    try:
        # Open the file and use a generator for streaming, without closing it prematurely
        file = open(file_path, 'rb')
        response = StreamingHttpResponse(
            file_stream(file, start, end),
            content_type=content_type
        )
        response['Content-Length'] = str(content_length)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        response['Last-Modified'] = http_date(os.path.getmtime(file_path))
        response.status_code = 206  # Partial content

        # Do not close the file here! Let Django handle it with StreamingHttpResponse
        return response
    except BrokenPipeError:
        print(
            f"Client disconnected during streaming: {request.META.get('REMOTE_ADDR')}")
        return HttpResponse(status=200)  # Return a simple OK response


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
        BASE_DIR, path))  # Normalize full path

    # Check if the path exists
    if not os.path.exists(full_path):
        raise Http404("Directory does not exist")

    items = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        relative_path = os.path.relpath(item_path, BASE_DIR)
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
            BASE_DIR, path))  # Normalize the path
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
