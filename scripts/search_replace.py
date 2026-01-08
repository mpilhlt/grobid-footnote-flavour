#!/usr/bin/env python3
"""
Search and replace utility for files and filenames with backup and restore capabilities.

This script provides a robust way to perform regex-based search and replace operations
across multiple files in a directory tree, with built-in backup and restore functionality.

Features:
    - Regex-based search and replace in file contents
    - Optional search and replace in file paths (directories and filenames)
    - Automatic backup creation before making changes
    - Dry-run mode for previewing changes
    - Detailed or summary reporting
    - Restore functionality from backups with automatic cleanup
    - Recursive directory traversal

Parameters:
    --search REGEX       Regular expression pattern to search for (required unless --restore)
    --replace EXPR       Replacement expression supporting regex backreferences (required unless --restore)
    --filepaths          Also search and replace in file paths (directories and filenames)
    --filepaths-only     Only modify file paths, skip file content changes (implies --filepaths)
    --dry-run            Show detailed report of what would be changed without making changes
    --backup-path PATH   Custom path to store backup (default: <parent>/<basename>-backup-YYYYMMDD_HHMMSS)
    --restore            Restore target folder from backup (deletes backup after successful restore)
    --yes                Skip confirmation prompts
    path                 Target folder path (required)

Examples:
    # Dry run to preview changes with detailed output
    ./search_replace.py --search "foo" --replace "bar" --dry-run /path/to/folder

    # Replace all occurrences in file contents
    ./search_replace.py --search "old_name" --replace "new_name" /path/to/folder

    # Replace in both file contents and file paths
    ./search_replace.py --search "old" --replace "new" --filepaths /path/to/folder

    # Replace only in file paths, not in file contents
    ./search_replace.py --search "old" --replace "new" --filepaths-only /path/to/folder

    # Replace with regex backreferences
    ./search_replace.py --search "(\d{4})-(\d{2})" --replace "\2/\1" /path/to/folder

    # Non-interactive mode (skip confirmation)
    ./search_replace.py --search "foo" --replace "bar" --yes /path/to/folder

    # Restore from default backup location
    ./search_replace.py --restore /path/to/folder

    # Restore from custom backup location
    ./search_replace.py --restore --backup-path /custom/backup /path/to/folder

    # Use custom backup location for search and replace
    ./search_replace.py --search "foo" --replace "bar" --backup-path /safe/backup /path/to/folder

Workflow:
    1. Creates backup of target folder (unless --dry-run)
    2. Recursively scans all files in target folder
    3. Identifies matches in file contents and optionally filenames
    4. Reports findings (detailed in dry-run mode, summary otherwise)
    5. Prompts for confirmation (unless --yes or --dry-run)
    6. Applies changes to file contents and filenames
    7. Preserves backup for potential restoration

Notes:
    - Binary files and files that cannot be decoded as UTF-8 are skipped
    - If no matches are found, the backup is automatically removed
    - Backup path must not exist (prevents accidental overwrites)
    - Path changes are processed in reverse order to handle nested paths correctly
    - New parent directories are created automatically when renaming paths
    - After successful restore, the backup is automatically deleted
"""

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import List, Tuple, Dict
from datetime import datetime


class SearchReplace:
    def __init__(
        self,
        search: str,
        replace: str,
        target_path: Path,
        backup_path: Path = None,
        filepaths: bool = False,
        filepaths_only: bool = False,
        dry_run: bool = False,
        skip_confirmation: bool = False,
    ):
        self.search_pattern = re.compile(search)
        self.replace = replace
        self.target_path = target_path
        self.backup_path = backup_path
        self.filepaths = filepaths or filepaths_only  # filepaths_only implies filepaths
        self.filepaths_only = filepaths_only
        self.dry_run = dry_run
        self.skip_confirmation = skip_confirmation

        # Results tracking
        self.file_matches: Dict[Path, List[Tuple[int, str, str]]] = {}
        self.path_changes: List[Tuple[Path, str]] = []

    def create_backup(self) -> bool:
        """Create a backup of the target folder."""
        if self.backup_path.exists():
            print(f"Error: Backup path already exists: {self.backup_path}")
            print("Please remove it or specify a different backup path.")
            return False

        try:
            print(f"Creating backup: {self.target_path} -> {self.backup_path}")
            shutil.copytree(self.target_path, self.backup_path)
            print("Backup created successfully.")
            return True
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False

    def scan_files(self):
        """Scan all files in target path for matches."""
        print(f"Scanning files in: {self.target_path}")
        print(f"Search pattern: {self.search_pattern.pattern}")
        print()

        for file_path in self.target_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Check path matches (full relative path from target)
            if self.filepaths:
                rel_path = file_path.relative_to(self.target_path)
                rel_path_str = str(rel_path)
                if self.search_pattern.search(rel_path_str):
                    new_rel_path_str = self.search_pattern.sub(self.replace, rel_path_str)
                    self.path_changes.append((file_path, new_rel_path_str))

            # Check file content matches (skip if filepaths_only)
            if not self.filepaths_only:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    matches = []
                    for line_num, line in enumerate(lines, 1):
                        if self.search_pattern.search(line):
                            new_line = self.search_pattern.sub(self.replace, line)
                            matches.append((line_num, line.rstrip('\n'), new_line.rstrip('\n')))

                    if matches:
                        self.file_matches[file_path] = matches

                except (UnicodeDecodeError, PermissionError):
                    # Skip binary files or files we can't read
                    continue

    def report_changes(self):
        """Report what would be or will be changed."""
        total_file_changes = sum(len(matches) for matches in self.file_matches.values())
        total_path_changes = len(self.path_changes)

        if self.dry_run:
            print("=" * 80)
            print("DRY RUN - Detailed report of changes that would be made:")
            print("=" * 80)
            print()

            if self.file_matches:
                print(f"CONTENT MATCHES ({len(self.file_matches)} files, {total_file_changes} changes):")
                print("-" * 80)
                for file_path, matches in sorted(self.file_matches.items()):
                    rel_path = file_path.relative_to(self.target_path)
                    print(f"\n{rel_path} ({len(matches)} matches):")
                    for line_num, old_line, new_line in matches:
                        print(f"  Line {line_num}:")
                        print(f"    - {old_line}")
                        print(f"    + {new_line}")
                print()

            if self.path_changes:
                print(f"PATH CHANGES ({total_path_changes} files):")
                print("-" * 80)
                for file_path, new_rel_path_str in sorted(self.path_changes):
                    rel_path = file_path.relative_to(self.target_path)
                    print(f"  {rel_path}")
                    print(f"  -> {new_rel_path_str}")
                print()

            if not self.file_matches and not self.path_changes:
                print("No matches found.")
        else:
            print("=" * 80)
            print("SUMMARY OF CHANGES:")
            print("=" * 80)
            print(f"Files with content changes: {len(self.file_matches)}")
            print(f"Total content replacements: {total_file_changes}")
            if self.filepaths:
                print(f"Path changes: {total_path_changes}")
            print()

        return total_file_changes > 0 or total_path_changes > 0

    def confirm_changes(self) -> bool:
        """Ask user for confirmation."""
        if self.skip_confirmation:
            return True

        response = input("Proceed with these changes? [y/N]: ").strip().lower()
        return response in ('y', 'yes')

    def apply_changes(self):
        """Apply the search and replace changes."""
        print("\nApplying changes...")

        # Apply content changes
        for file_path, matches in self.file_matches.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                new_content = self.search_pattern.sub(self.replace, content)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        # Apply path changes (process in reverse order to handle nested paths)
        # We need to rename from deepest to shallowest to avoid issues with parent dirs
        old_dirs = set()
        for file_path, new_rel_path_str in sorted(self.path_changes, reverse=True):
            try:
                new_path = self.target_path / new_rel_path_str
                # Create parent directories if they don't exist
                new_path.parent.mkdir(parents=True, exist_ok=True)

                # Track old parent directories for cleanup
                old_parent = file_path.parent
                while old_parent != self.target_path:
                    old_dirs.add(old_parent)
                    old_parent = old_parent.parent

                file_path.rename(new_path)
            except Exception as e:
                print(f"Error renaming {file_path}: {e}")

        # Remove empty directories left behind (from deepest to shallowest)
        for old_dir in sorted(old_dirs, reverse=True):
            try:
                if old_dir.exists() and old_dir.is_dir() and not any(old_dir.iterdir()):
                    old_dir.rmdir()
            except Exception:
                # Directory not empty or other error, skip it
                pass

        print("Changes applied successfully.")

    def run(self):
        """Execute the search and replace operation."""
        # Create backup unless dry run
        if not self.dry_run:
            if not self.create_backup():
                return False
            print()

        # Scan for matches
        self.scan_files()

        # Report findings
        has_changes = self.report_changes()

        if not has_changes:
            print("No changes to make.")
            if not self.dry_run and self.backup_path.exists():
                print(f"Removing unnecessary backup: {self.backup_path}")
                shutil.rmtree(self.backup_path)
            return True

        # If dry run, we're done
        if self.dry_run:
            return True

        # Confirm and apply changes
        if not self.confirm_changes():
            print("Operation cancelled.")
            if self.backup_path.exists():
                print(f"Backup preserved at: {self.backup_path}")
            return False

        self.apply_changes()
        print(f"\nBackup available at: {self.backup_path}")
        return True


def restore_from_backup(backup_path: Path, target_path: Path, skip_confirmation: bool = False):
    """Restore the target folder from backup."""
    if not backup_path.exists():
        print(f"Error: Backup path does not exist: {backup_path}")
        return False

    if not backup_path.is_dir():
        print(f"Error: Backup path is not a directory: {backup_path}")
        return False

    print(f"Restore operation:")
    print(f"  From: {backup_path}")
    print(f"  To:   {target_path}")
    print()

    if target_path.exists():
        print("Warning: Target path exists and will be removed!")

    if not skip_confirmation:
        response = input("Proceed with restore? [y/N]: ").strip().lower()
        if response not in ('y', 'yes'):
            print("Restore cancelled.")
            return False

    try:
        if target_path.exists():
            print(f"Removing existing target: {target_path}")
            shutil.rmtree(target_path)

        print(f"Restoring from backup...")
        shutil.copytree(backup_path, target_path)
        print("Restore completed successfully.")

        # Delete the backup after successful restore
        print(f"Removing backup: {backup_path}")
        shutil.rmtree(backup_path)
        print("Backup removed.")

        return True
    except Exception as e:
        print(f"Error during restore: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Search and replace utility for files and filenames with backup capabilities.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to preview changes with detailed output
  %(prog)s --search "foo" --replace "bar" --dry-run /path/to/folder

  # Replace all occurrences in file contents
  %(prog)s --search "old_name" --replace "new_name" /path/to/folder

  # Replace in both file contents and file paths
  %(prog)s --search "old" --replace "new" --filepaths /path/to/folder

  # Replace only in file paths, not in file contents
  %(prog)s --search "old" --replace "new" --filepaths-only /path/to/folder

  # Replace with regex backreferences
  %(prog)s --search "(\\d{4})-(\\d{2})" --replace "\\2/\\1" /path/to/folder

  # Non-interactive mode (skip confirmation)
  %(prog)s --search "foo" --replace "bar" --yes /path/to/folder

  # Restore from default backup location
  %(prog)s --restore /path/to/folder

  # Restore from custom backup location
  %(prog)s --restore --backup-path /custom/backup /path/to/folder

  # Use custom backup location for search and replace
  %(prog)s --search "foo" --replace "bar" --backup-path /safe/backup /path/to/folder
        """
    )

    parser.add_argument(
        '--search',
        type=str,
        help='Regular expression pattern to search for (required unless --restore)'
    )

    parser.add_argument(
        '--replace',
        type=str,
        help='Replacement expression (required unless --restore)'
    )

    parser.add_argument(
        '--filepaths',
        action='store_true',
        help='Also search and replace in file paths (directories and filenames)'
    )

    parser.add_argument(
        '--filepaths-only',
        action='store_true',
        help='Only modify file paths, skip file content changes (implies --filepaths)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show detailed report of what would be changed without making changes'
    )

    parser.add_argument(
        '--backup-path',
        type=Path,
        help='Path to store backup (default: <parent>/<basename>-backup-YYYYMMDD_HHMMSS)'
    )

    parser.add_argument(
        '--restore',
        action='store_true',
        help='Restore target folder from backup'
    )

    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompts'
    )

    parser.add_argument(
        'path',
        type=Path,
        help='Target folder path'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.restore:
        # Restore mode
        if args.search or args.replace:
            parser.error("--search and --replace cannot be used with --restore")

        target_path = args.path.resolve()

        if args.backup_path:
            backup_path = args.backup_path.resolve()
        else:
            backup_path = target_path.parent / f"{target_path.name}-backup"

        success = restore_from_backup(backup_path, target_path, args.yes)
        sys.exit(0 if success else 1)
    else:
        # Search and replace mode
        if not args.search:
            parser.error("--search is required")
        if not args.replace:
            parser.error("--replace is required")

        target_path = args.path.resolve()

        if not target_path.exists():
            print(f"Error: Target path does not exist: {target_path}")
            sys.exit(1)

        if not target_path.is_dir():
            print(f"Error: Target path is not a directory: {target_path}")
            sys.exit(1)

        # Determine backup path
        if args.backup_path:
            backup_path = args.backup_path.resolve()
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = target_path.parent / f"{target_path.name}-backup-{timestamp}"

        # Run search and replace
        sr = SearchReplace(
            search=args.search,
            replace=args.replace,
            target_path=target_path,
            backup_path=backup_path,
            filepaths=args.filepaths,
            filepaths_only=args.filepaths_only,
            dry_run=args.dry_run,
            skip_confirmation=args.yes,
        )

        success = sr.run()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
