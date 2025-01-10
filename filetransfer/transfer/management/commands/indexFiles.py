import os
import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from transfer.models import FileMetadata, FileTypeCategory
from tqdm import tqdm  # Import tqdm for progress bar
from itertools import islice

# List of base directories to index
BASE_DIRS = ['C:\\', 'D:\\']  # Add more directories as needed

# Batch size for database operations
BATCH_SIZE = 500


def chunked_queryset(iterable, size):
    """Helper function to split an iterable into chunks of a given size."""
    iterator = iter(iterable)
    for first in iterator:
        yield [first] + list(islice(iterator, size - 1))


class Command(BaseCommand):
    help = 'Efficiently sync filesystem changes to the database.'

    def handle(self, *args, **kwargs):
        # Keep track of indexed paths
        indexed_paths = set()

        # Build a mapping of extensions to FileTypeCategory
        extension_to_category = {}
        for category in FileTypeCategory.objects.all():
            extensions = category.get_extensions_list()
            for ext in extensions:
                extension_to_category[ext] = category

        # First pass: Walk over directories and collect filesystem state
        self.stdout.write("Indexing filesystem...")

        # Create tqdm progress bar for directories and files
        total_files = sum(len(dirs) + len(files)
                          for _, dirs, files in os.walk(BASE_DIRS[0]))
        with tqdm(total=total_files, desc="Processing Files", unit="file") as pbar:
            for BASE_DIR in BASE_DIRS:
                for root, dirs, files in os.walk(BASE_DIR):
                    # Process directories
                    for directory in dirs:
                        dir_path = os.path.join(root, directory)
                        relative_path = os.path.relpath(dir_path, BASE_DIR)  # Calculate relative to BASE_DIR
                        absolute_path = os.path.abspath(dir_path)
                        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(dir_path))
                        created = datetime.datetime.fromtimestamp(os.path.getctime(dir_path))

                        last_modified = timezone.make_aware(last_modified)
                        created = timezone.make_aware(created)

                        indexed_paths.add(absolute_path)

                        # Add directory to the database
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

                        pbar.update(1)  # Update progress bar for directory

                    # Process files
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, BASE_DIR)  # Calculate relative to BASE_DIR
                        absolute_path = os.path.abspath(file_path)
                        file_size = os.path.getsize(file_path)
                        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                        created = datetime.datetime.fromtimestamp(os.path.getctime(file_path))

                        last_modified = timezone.make_aware(last_modified)
                        created = timezone.make_aware(created)

                        indexed_paths.add(absolute_path)

                        ext = os.path.splitext(file)[1].lower()
                        file_type = extension_to_category.get(ext)

                        # Add file to the database
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

                        pbar.update(1)  # Update progress bar for file



                    # Process files
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, BASE_DIR)
                        absolute_path = os.path.abspath(file_path)
                        file_size = os.path.getsize(file_path)
                        last_modified = datetime.datetime.fromtimestamp(
                            os.path.getmtime(file_path))
                        created = datetime.datetime.fromtimestamp(
                            os.path.getctime(file_path))

                        last_modified = timezone.make_aware(last_modified)
                        created = timezone.make_aware(created)

                        indexed_paths.add(absolute_path)

                        ext = os.path.splitext(file)[1].lower()
                        file_type = extension_to_category.get(ext)

                        # Add file to the database
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

                        pbar.update(1)  # Update progress bar for file

        # Second pass: Remove outdated entries from the database
        self.stdout.write("Cleaning up removed entries...")
        all_paths_in_db = FileMetadata.objects.values_list(
            'absolute_path', flat=True)
        paths_to_delete = set(all_paths_in_db) - indexed_paths

        # Create tqdm progress bar for deletion
        with tqdm(total=len(paths_to_delete), desc="Deleting Removed Files", unit="file") as pbar:
            for chunk in chunked_queryset(paths_to_delete, BATCH_SIZE):
                FileMetadata.objects.filter(absolute_path__in=chunk).delete()
                pbar.update(len(chunk))  # Update progress bar for deletions

        self.stdout.write(self.style.SUCCESS("Filesystem sync completed."))
