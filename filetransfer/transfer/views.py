from django.shortcuts import render
from django.http import HttpResponse, Http404
import os
import zipfile
import tempfile
import datetime
from PIL import Image
import shutil
from wsgiref.util import FileWrapper
from django.http import StreamingHttpResponse, Http404, FileResponse
from django.utils.http import http_date
import mimetypes
import re
from moviepy.editor import VideoFileClip
import py7zr
import hashlib
import subprocess
from django.utils.encoding import smart_str


BASE_DIR = 'D:\\'  # Change this to the base directory you want to start with
BASE_DIR = 'D:\\'  # Adjust this according to your environment
ARCHIVE_STORAGE_DIR = os.path.join(BASE_DIR, 'archive_storage')
os.makedirs(ARCHIVE_STORAGE_DIR, exist_ok=True)


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

            if uploaded_file.name.lower().endswith(('.mp4', '.avi', '.mov', '.webm', '.mkv')):
                clip = VideoFileClip(file_path)
                frame = clip.get_frame(t=1)  # Get frame at 1 second
                img = Image.fromarray(frame)
                img.thumbnail((100, 100))
                thumbnail_path = os.path.join(
                    upload_dir, f'thumb_{uploaded_file.name}.jpg')
                img.save(thumbnail_path, 'JPEG')
                thumbnails.append(os.path.basename(thumbnail_path))

            uploaded_file_paths.append(file_path)

        # Return the list of uploaded file paths and thumbnails
        return render(request, 'upload.html', {
            'file_paths': uploaded_file_paths,
            'thumbnails': thumbnails
        })
    return render(request, 'upload.html')


def file_list(request, path=''):
    full_path = os.path.join(BASE_DIR, path)
    if not os.path.exists(full_path):
        raise Http404("Directory does not exist")

    # Default size is 100x100
    thumbnail_size = int(request.GET.get('thumbnail_size', 100))

    # Temporary thumbnail directory
    temp_dir = os.path.join(BASE_DIR, 'temp_thumbnails')
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)

    video_extensions = ('.mp4', '.avi', '.mov', '.webm', '.mkv')

    items = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        is_video = not os.path.isdir(
            item_path) and item.lower().endswith(video_extensions)
        # Include the relative path correctly
        relative_path = os.path.join(path, item)
        item_info = {
            'name': item,
            'path': path,  # Pass the current directory path
            'relative_path': relative_path,  # Include the full relative path to the file
            'is_dir': os.path.isdir(item_path),
            'size': os.path.getsize(item_path),
            'modified': datetime.datetime.fromtimestamp(os.path.getmtime(item_path)),
            'thumbnail': None,
            'is_video': is_video  # Add this key to determine if the file is a video
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
        'current_path': path,  # Ensure current path is passed to the template
        'thumbnail_size': thumbnail_size
    }
    return render(request, 'file_list.html', context)


# def serve_thumbnail(request, filename):
#     file_path = os.path.join(BASE_DIR, 'temp_thumbnails', filename)
#     if os.path.exists(file_path):
#         with open(file_path, 'rb') as f:
#             if filename.endswith('.png'):
#                 content_type = 'image/png'
#             else:
#                 content_type = 'image/jpeg'
#             return HttpResponse(f.read(), content_type=content_type)
#     raise Http404("Thumbnail does not exist")


def download_file(request, path, filename):
    file_path = os.path.join(BASE_DIR, path, filename)
    if not os.path.exists(file_path):
        raise Http404("File does not exist")

    if os.path.isdir(file_path):
        zip_subdir = filename
        zip_filename = f"{zip_subdir}.7z"

        # Create 'temparchive' directory if it doesn't exist
        temp_archive_dir = os.path.join(BASE_DIR, 'temparchive')
        os.makedirs(temp_archive_dir, exist_ok=True)

        # Create a unique subdirectory within 'temparchive' for this archive
        unique_subdir = os.path.join(temp_archive_dir, zip_subdir)
        os.makedirs(unique_subdir, exist_ok=True)

        # Path to the archive file
        archive_path = os.path.join(unique_subdir, zip_filename)

        # Check if the archive already exists
        if not os.path.exists(archive_path):
            # Create the 7z archive
            with py7zr.SevenZipFile(archive_path, 'w', filters=[{'id': py7zr.FILTER_COPY}]) as archive:
                for root, dirs, files in os.walk(file_path):
                    # Preserve the directory structure by using the relative path
                    relative_dir = os.path.relpath(
                        root, os.path.join(file_path, '..'))
                    for file in files:
                        file_full_path = os.path.join(root, file)
                        # Add files to the archive, preserving the directory structure
                        arcname = os.path.join(relative_dir, file)
                        archive.write(file_full_path, arcname)

        # Open the archive file for streaming the response
        response = FileResponse(open(archive_path, 'rb'),
                                as_attachment=True, filename=zip_filename)
        response['Content-Type'] = 'application/x-7z-compressed'
        # Indicate that the server accepts byte-range requests
        response['Accept-Ranges'] = 'bytes'
        return response

    else:
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
