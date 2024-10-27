import os
import sys
from datetime import timedelta
from django.core.management.base import BaseCommand
from transfer.models import Movie
from moviepy.editor import VideoFileClip
from django.conf import settings

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.webm', '.mkv')
BASE_DIR = 'D:\\'  # Update this to your storage base directory
# Directories to exclude
EXCLUDE_DIRS = {'$RECYCLE.BIN', 'System Volume Information'}


class Command(BaseCommand):
    help = 'Index video files in the base directory and generate thumbnails'

    def handle(self, *args, **kwargs):
        # Create a set of existing file paths to skip
        existing_files = set(Movie.objects.values_list('file_path', flat=True))

        for root, dirs, files in os.walk(BASE_DIR):
            # Exclude specific directories
            dirs[:] = [
                d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('$')]

            for file in files:
                if file.lower().endswith(VIDEO_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    if file_path in existing_files:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping (already indexed): {file_path}'))
                        continue  # Skip files already in the database

                    # Check if the file is valid before processing
                    if not os.path.isfile(file_path) or os.path.getsize(file_path) == 0:
                        self.stdout.write(
                            self.style.ERROR(f'Skipping invalid file: {file_path}'))
                        continue

                    try:
                        # Process video file
                        clip = VideoFileClip(file_path)
                        duration = timedelta(seconds=clip.duration)
                        clip.reader.close()
                        if clip.audio:
                            clip.audio.reader.close_proc()

                        # Save to database
                        movie = Movie.objects.create(
                            file_name=file,
                            movie_name=os.path.splitext(file)[0],
                            file_path=file_path,
                            length=duration,
                        )

                        # Generate thumbnail
                        self.generate_thumbnail(movie)

                        self.stdout.write(self.style.SUCCESS(
                            f'Indexed and generated thumbnail: {file_path}'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f'Failed to process {file_path}: {e}'))
        self.stdout.write(self.style.SUCCESS('Video indexing completed.'))

    def generate_thumbnail(self, movie):
        import subprocess

        # Ensure the thumbnails directory exists
        thumbnails_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
        os.makedirs(thumbnails_dir, exist_ok=True)

        thumbnail_path = os.path.join(thumbnails_dir, f'{movie.id}.jpg')

        # Use FFmpeg to generate the thumbnail
        try:
            result = subprocess.run([
                'ffmpeg',
                '-y',
                '-loglevel', 'error',
                '-ss', '00:00:10',
                '-i', movie.file_path,
                '-frames:v', '1',
                '-q:v', '2',
                thumbnail_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0:
                # FFmpeg failed; log the error and skip
                self.stdout.write(self.style.ERROR(
                    f'FFmpeg failed for {movie.file_path}: {result.stderr.strip()}'))
                return  # Exit the function without saving the thumbnail

            # Update the movie instance with the thumbnail path
            movie.thumbnail.name = f'thumbnails/{movie.id}.jpg'
            movie.save()
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Failed to generate thumbnail for {movie.file_path}: {e}'))
