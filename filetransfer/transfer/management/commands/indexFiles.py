import os
import datetime
from django.core.management.base import BaseCommand
from transfer.models import FileMetadata, FileTypeCategory

# List of base directories to index
BASE_DIRS = ['D:\\']  # Add more directories as needed


class Command(BaseCommand):
    help = 'Index files and directories in the base directory and update metadata in the database.'

    def handle(self, *args, **kwargs):
        # Keep track of paths that are being indexed to remove outdated entries later
        indexed_paths = set()

        # Build a mapping of extensions to FileTypeCategory
        extension_to_category = {}
        for category in FileTypeCategory.objects.all():
            extensions = category.get_extensions_list()
            for ext in extensions:
                extension_to_category[ext] = category

        for BASE_DIR in BASE_DIRS:
            for root, dirs, files in os.walk(BASE_DIR):
                # Index directories
                for directory in dirs:
                    dir_path = os.path.join(root, directory)
                    relative_path = os.path.relpath(dir_path, BASE_DIR)
                    absolute_path = os.path.abspath(dir_path)
                    last_modified = datetime.datetime.fromtimestamp(
                        os.path.getmtime(dir_path)
                    )
                    created = datetime.datetime.fromtimestamp(
                        os.path.getctime(dir_path)
                    )

                    indexed_paths.add(absolute_path)

                    # Update or create the directory entry
                    FileMetadata.objects.update_or_create(
                        absolute_path=absolute_path,
                        defaults={
                            'name': directory,
                            'relative_path': relative_path,
                            'is_dir': True,
                            'size': None,
                            'modified': last_modified,
                            'created': created,
                            'file_type': None,
                        }
                    )

                # Index files
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, BASE_DIR)
                    absolute_path = os.path.abspath(file_path)
                    file_size = os.path.getsize(file_path)
                    last_modified = datetime.datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    )
                    created = datetime.datetime.fromtimestamp(
                        os.path.getctime(file_path)
                    )

                    indexed_paths.add(absolute_path)

                    # Determine the file type based on extension
                    ext = os.path.splitext(file)[1].lower()
                    file_type = extension_to_category.get(ext)

                    # Update or create the file entry
                    FileMetadata.objects.update_or_create(
                        absolute_path=absolute_path,
                        defaults={
                            'name': file,
                            'relative_path': relative_path,
                            'is_dir': False,
                            'size': file_size,
                            'modified': last_modified,
                            'created': created,
                            'file_type': file_type,
                        }
                    )

        # Optional: Remove any entries in the database that were not re-indexed (deleted from the file system)
        FileMetadata.objects.exclude(absolute_path__in=indexed_paths).delete()

        self.stdout.write(self.style.SUCCESS(
            'File indexing completed and database updated.'))
