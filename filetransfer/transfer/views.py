from django.shortcuts import render
from django.http import HttpResponse, Http404
import os
import zipfile
import tempfile
import datetime
from PIL import Image
import shutil
from wsgiref.util import FileWrapper
from django.http import StreamingHttpResponse, Http404
from django.utils.http import http_date
import mimetypes
import re
from moviepy.editor import VideoFileClip


BASE_DIR = 'D:\\'  # Change this to the base directory you want to start with


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

                    thumbnail_filename = f"thumb_{os.path.basename(item)}{thumbnail_ext}"
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


def serve_thumbnail(request, filename):
    file_path = os.path.join(BASE_DIR, 'temp_thumbnails', filename)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            if filename.endswith('.png'):
                content_type = 'image/png'
            else:
                content_type = 'image/jpeg'
            return HttpResponse(f.read(), content_type=content_type)
    raise Http404("Thumbnail does not exist")


def download_file(request, path, filename):
    file_path = os.path.join(BASE_DIR, path, filename)
    if not os.path.exists(file_path):
        raise Http404("File does not exist")

    if os.path.isdir(file_path):
        zip_subdir = filename
        zip_filename = f"{zip_subdir}.zip"

        # Create a temporary file to store the zip
        s = tempfile.TemporaryFile()
        with zipfile.ZipFile(s, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(file_path):
                # Preserve the directory structure by using the relative path
                relative_dir = os.path.relpath(
                    root, os.path.join(file_path, '..'))
                for file in files:
                    file_full_path = os.path.join(root, file)
                    # Create the correct arcname to preserve the subdirectory structure
                    arcname = os.path.join(relative_dir, file)
                    zf.write(file_full_path, arcname)

        s.seek(0)
        response = StreamingHttpResponse(s, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename={zip_filename}'
        return response
    else:
        # Stream the file in chunks instead of loading it all at once
        def file_iterator(file_name, chunk_size=8192):
            with open(file_name, 'rb') as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        response = StreamingHttpResponse(file_iterator(file_path))
        response['Content-Type'] = 'application/force-download'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


def stream_video(request, path, filename):
    # file_path = os.path.join(BASE_DIR, path, filename)
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

    try:
        response = StreamingHttpResponse(
            FileWrapper(open(file_path, 'rb'), blksize=512),
            content_type=content_type,
        )
        response['Content-Length'] = str(content_length)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        response['Last-Modified'] = http_date(os.path.getmtime(file_path))
        response.status_code = 206  # Partial content
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
