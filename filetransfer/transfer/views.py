from django.shortcuts import render
from django.http import HttpResponse, Http404
import os
import zipfile
import tempfile
import datetime
from PIL import Image
import shutil

BASE_DIR = 'D:\\'  # Change this to the base directory you want to start with


def file_upload(request):
    if request.method == 'POST' and request.FILES['file']:
        uploaded_file = request.FILES['file']
        with open(os.path.join(BASE_DIR, uploaded_file.name), 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        return HttpResponse("File uploaded successfully.")
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

    items = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        item_info = {
            'name': item,
            'path': path,
            'is_dir': os.path.isdir(item_path),
            'size': os.path.getsize(item_path),
            'modified': datetime.datetime.fromtimestamp(os.path.getmtime(item_path)),
            'thumbnail': None
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
        'current_path': path,
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

        s = tempfile.TemporaryFile()
        zf = zipfile.ZipFile(s, "w")

        for dirname, subdirs, files in os.walk(file_path):
            for fname in files:
                file_path = os.path.join(dirname, fname)
                parent_path = os.path.relpath(
                    file_path, os.path.join(file_path, '..'))
                arcname = os.path.join(zip_subdir, parent_path)
                zf.write(file_path, arcname)
        zf.close()

        s.seek(0)
        response = HttpResponse(s, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename={zip_filename}'
        return response
    else:
        with open(file_path, 'rb') as file:
            response = HttpResponse(
                file, content_type='application/force-download')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
