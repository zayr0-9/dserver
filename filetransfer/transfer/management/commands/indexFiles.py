import os
import datetime
from django.core.management.base import BaseCommand
from transfer.models import FileMetadata

BASE_DIR = 'D:\\'  # Root directory to index


class Command(BaseCommand):
    help = 'Index files and directories in the base directory and update metadata in the database.'

    def handle(self, *args, **kwargs):
        # Keep track of paths that are being indexed to remove outdated entries later
        indexed_paths = set()

        for root, dirs, files in os.walk(BASE_DIR):
            # Index directories
            for directory in dirs:
                dir_path = os.path.join(root, directory)
                relative_path = os.path.relpath(dir_path, BASE_DIR)
                last_modified = datetime.datetime.fromtimestamp(
                    os.path.getmtime(dir_path)
                )

                indexed_paths.add(relative_path)

                # Check if the directory already exists in the database
                try:
                    directory_entry = FileMetadata.objects.get(
                        file_path=relative_path, is_dir=True)
                    # Update the metadata if it already exists
                    directory_entry.last_modified = last_modified
                    directory_entry.save()
                except FileMetadata.DoesNotExist:
                    # Create a new entry if the directory does not exist
                    FileMetadata.objects.create(
                        file_name=directory,
                        file_path=relative_path,
                        is_dir=True,
                        file_size=None,  # Directories don't have a size
                        last_modified=last_modified,
                    )

            # Index files
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, BASE_DIR)
                file_size = os.path.getsize(file_path)
                last_modified = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                )

                indexed_paths.add(relative_path)

                # Check if the file already exists in the database
                try:
                    file_entry = FileMetadata.objects.get(
                        file_path=relative_path, is_dir=False)
                    # Update the metadata if it already exists
                    file_entry.file_size = file_size
                    file_entry.last_modified = last_modified
                    file_entry.save()
                except FileMetadata.DoesNotExist:
                    # Create a new entry if the file does not exist
                    FileMetadata.objects.create(
                        file_name=file,
                        file_path=relative_path,
                        is_dir=False,
                        file_size=file_size,
                        last_modified=last_modified,
                    )

        # Optional: Remove any entries in the database that were not re-indexed (deleted from the file system)
        FileMetadata.objects.exclude(file_path__in=indexed_paths).delete()

        self.stdout.write(self.style.SUCCESS(
            'File indexing completed and database updated.'))
