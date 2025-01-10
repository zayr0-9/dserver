import os
import datetime
from itertools import islice

from django.utils import timezone
from django.core.management.base import BaseCommand
from tqdm import tqdm

from transfer.models import FileMetadata, FileTypeCategory

# List of base directories to index
BASE_DIRS = ['C:\\', 'D:\\']  # Add more directories as needed

# Batch size for database delete operations
BATCH_SIZE = 500


def chunked_queryset(iterable, size):
    """
    Helper function to split an iterable into chunks of a given size.
    """
    iterator = iter(iterable)
    for first in iterator:
        yield [first] + list(islice(iterator, size - 1))


def get_total_entries(base_dirs):
    """
    Return total count of directories + files across all given base directories.
    This is useful for the progress bar initialization.
    """
    total = 0
    for base_dir in base_dirs:
        for _, dirs, files in os.walk(base_dir):
            total += len(dirs) + len(files)
    return total


def process_file(
    absolute_path,
    base_dir,
    file_name,
    extension_to_category,
    indexed_paths,
):
    """
    Process a single file: get metadata, store/update in DB.
    """
    # Attempt to compute relative path. If the path is invalid or on a different mount,
    # skip or gracefully handle.
    try:
        relative_path = os.path.relpath(absolute_path, base_dir)
    except ValueError:
        # If Windows raises "path is on mount '\\\\.\\NUL', start on mount 'C:'"
        # you can either skip or store the absolute_path as fallback.
        # We'll just skip these special files for now.
        return

    try:
        file_size = os.path.getsize(absolute_path)
        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(absolute_path))
        created = datetime.datetime.fromtimestamp(os.path.getctime(absolute_path))
    except OSError:
        # In case of permission error or other OS-level issues, skip
        return

    # Convert datetimes to timezone-aware
    last_modified = timezone.make_aware(last_modified)
    created = timezone.make_aware(created)

    indexed_paths.add(absolute_path)

    # Determine file type from extension
    ext = os.path.splitext(file_name)[1].lower()
    file_type = extension_to_category.get(ext)

    FileMetadata.objects.update_or_create(
        absolute_path=absolute_path,
        defaults={
            'name': file_name,
            'relative_path': relative_path,
            'is_dir': False,
            'size': file_size,
            'modified': last_modified,
            'created': created,
            'file_type': file_type,
        },
    )


class Command(BaseCommand):
    help = 'Efficiently sync filesystem changes to the database.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Building extension-to-category mapping...")
        # Build a mapping of extensions to FileTypeCategory for quick lookups
        extension_to_category = {}
        for category in FileTypeCategory.objects.all():
            for ext in category.get_extensions_list():
                extension_to_category[ext.lower()] = category

        # Keep track of indexed paths
        indexed_paths = set()

        self.stdout.write("Calculating total entries for progress bar...")
        total_entries = get_total_entries(BASE_DIRS)
        self.stdout.write(f"Total entries to process: {total_entries}")

        # Create a progress bar for directories and files
        with tqdm(total=total_entries, desc="Indexing Files", unit="file") as pbar:
            # Go through each base directory
            for base_dir in BASE_DIRS:
                for root, dirs, files in os.walk(base_dir):
                    # --- Process directories ---
                    for directory in dirs:
                        dir_path = os.path.join(root, directory)
                        absolute_path = os.path.abspath(dir_path)

                        try:
                            # Attempt to compute relative path
                            relative_path = os.path.relpath(dir_path, base_dir)
                        except ValueError:
                            # Skip special paths on different mounts
                            pbar.update(1)
                            continue

                        try:
                            last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(dir_path))
                            created = datetime.datetime.fromtimestamp(os.path.getctime(dir_path))
                        except OSError:
                            # In case of permission errors or other OS issues
                            pbar.update(1)
                            continue

                        # Convert to timezone-aware
                        last_modified = timezone.make_aware(last_modified)
                        created = timezone.make_aware(created)

                        indexed_paths.add(absolute_path)

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
                        pbar.update(1)

                    # --- Process files ---
                    for file in files:
                        file_path = os.path.join(root, file)
                        absolute_path = os.path.abspath(file_path)
                        process_file(
                            absolute_path=absolute_path,
                            base_dir=base_dir,
                            file_name=file,
                            extension_to_category=extension_to_category,
                            indexed_paths=indexed_paths,
                        )
                        pbar.update(1)

        # --- SECOND PASS: REMOVE OUTDATED ENTRIES ---
        self.stdout.write("Cleaning up removed entries...")
        all_paths_in_db = FileMetadata.objects.values_list('absolute_path', flat=True)
        paths_to_delete = set(all_paths_in_db) - indexed_paths

        with tqdm(total=len(paths_to_delete), desc="Deleting Removed Files", unit="file") as pbar:
            for chunk in chunked_queryset(paths_to_delete, BATCH_SIZE):
                FileMetadata.objects.filter(absolute_path__in=chunk).delete()
                pbar.update(len(chunk))

        self.stdout.write(self.style.SUCCESS("Filesystem sync completed."))
