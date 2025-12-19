#!/usr/bin/env python3
"""
Download sample PDFs from the CSV file.

This script processes the oa_law_review_samples_with_footnotes.csv file by:
- Downloading 10 PDFs (2 from each of 5 different journals)
- Prioritizing journals without any previous downloads
- Marking successful downloads in the "downloaded" column
"""

import csv
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote
import time
from collections import defaultdict

# Configuration
CSV_FILE = "data/oa_law_review_samples_with_footnotes.csv"
PDF_FOLDER = "pdf"
PDFS_PER_JOURNAL = 2
NUM_JOURNALS = 5
TOTAL_PDFS = PDFS_PER_JOURNAL * NUM_JOURNALS


def ensure_pdf_folder():
    """Create the PDF folder if it doesn't exist."""
    Path(PDF_FOLDER).mkdir(parents=True, exist_ok=True)


def read_csv_with_downloaded_column(csv_path):
    """Read the CSV file and ensure it has a 'downloaded' column."""
    rows = []
    fieldnames = []
    has_downloaded_column = False

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        # Check if 'downloaded' column exists
        if 'downloaded' in fieldnames:
            has_downloaded_column = True
        else:
            fieldnames = list(fieldnames) + ['downloaded']

        for row in reader:
            if not has_downloaded_column:
                row['downloaded'] = ''
            rows.append(row)

    return rows, fieldnames


def write_csv(csv_path, rows, fieldnames):
    """Write the updated data back to the CSV file."""
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def get_journal_download_stats(rows):
    """Get download statistics for each journal."""
    journal_stats = defaultdict(lambda: {'total': 0, 'downloaded': 0})

    for row in rows:
        journal = row['journal']
        journal_stats[journal]['total'] += 1
        if row.get('downloaded', '').lower() == 'yes':
            journal_stats[journal]['downloaded'] += 1

    return journal_stats


def get_sorted_journals_by_priority(rows):
    """
    Get all journals sorted by download priority.
    Prioritize journals without any downloads.

    Returns:
        List of journal names sorted by priority (fewest downloads first)
    """
    journal_stats = get_journal_download_stats(rows)

    # Sort journals by number of downloads (ascending), then alphabetically
    sorted_journals = sorted(
        journal_stats.items(),
        key=lambda x: (x[1]['downloaded'], x[0])
    )

    return [journal for journal, stats in sorted_journals]


def encode_doi_for_filename(doi):
    """
    Encode a DOI for use as a filename.

    Rules:
    1. Replace slashes ("/") with double underscore ("__")
    2. Percent-encode all other special characters incompatible with POSIX or Windows filesystems

    Args:
        doi: The DOI string (with or without the https://doi.org/ prefix)

    Returns:
        A filesystem-safe filename string
    """
    # Remove the https://doi.org/ prefix if present
    if doi.startswith('https://doi.org/'):
        doi = doi[16:]  # len('https://doi.org/') = 16
    elif doi.startswith('http://doi.org/'):
        doi = doi[15:]  # len('http://doi.org/') = 15

    # First, replace slashes with double underscore
    doi = doi.replace('/', '__')

    # Then percent-encode special characters
    # quote() with safe='' will encode everything except alphanumeric and '_.-~'
    # We want to keep underscores (including our double underscores) and some basic chars
    # Characters that are safe: alphanumeric, underscore, hyphen, period
    doi = quote(doi, safe='_-.')

    return doi


def download_pdf(url, output_path, row_index):
    """Download a PDF from the given URL."""
    try:
        # Add a user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ResearchBot/1.0; +mailto:research@example.com)'
        }
        request = Request(url, headers=headers)

        print(f"  Downloading from: {url}")

        with urlopen(request, timeout=30) as response:
            content = response.read()

            # Verify it's a PDF (basic check)
            if not content.startswith(b'%PDF'):
                print(f"  WARNING: Content doesn't appear to be a PDF")
                return False

            with open(output_path, 'wb') as f:
                f.write(content)

            print(f"  ✓ Saved to: {output_path}")
            return True

    except HTTPError as e:
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        return False
    except URLError as e:
        print(f"  ✗ URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False


def main():
    """Main execution function."""
    ensure_pdf_folder()

    print(f"Reading CSV file: {CSV_FILE}")
    rows, fieldnames = read_csv_with_downloaded_column(CSV_FILE)
    print(f"Total rows in CSV: {len(rows)}")

    # Get journal statistics
    journal_stats = get_journal_download_stats(rows)
    print(f"\nJournal download statistics:")
    for journal, stats in sorted(journal_stats.items()):
        print(f"  {journal}: {stats['downloaded']}/{stats['total']} downloaded")

    # Get all journals sorted by priority
    journals_by_priority = get_sorted_journals_by_priority(rows)

    # Download PDFs
    downloads_successful = 0
    downloads_per_journal = defaultdict(int)
    attempted_per_journal = defaultdict(int)
    active_journals = set()

    print(f"\nStarting downloads (target: {TOTAL_PDFS} PDFs, {PDFS_PER_JOURNAL} per journal)...")

    # Keep trying until we have enough successful downloads or run out of PDFs
    for i, row in enumerate(rows):
        if downloads_successful >= TOTAL_PDFS:
            break

        journal = row['journal']

        # Skip if already downloaded or unavailable
        download_status = row.get('downloaded', '').lower()
        if download_status in ['yes', 'unavailable']:
            continue

        # Dynamically determine if we should use this journal
        # Add journals to active set as needed to reach our target
        if journal not in active_journals:
            # Check if we need more journals
            if len(active_journals) < NUM_JOURNALS:
                # Add this journal if it's in our priority list
                if journal in journals_by_priority:
                    active_journals.add(journal)
            # If we have enough active journals but some haven't yielded enough downloads,
            # we might need to add more
            elif downloads_successful + (len(active_journals) * PDFS_PER_JOURNAL - sum(downloads_per_journal.values())) < TOTAL_PDFS:
                # We're running short, add more journals
                if journal in journals_by_priority and journal not in active_journals:
                    active_journals.add(journal)
                    print(f"\n  Adding journal to active set: {journal}")

        # Skip if not in active journals
        if journal not in active_journals:
            continue

        # Skip if we've already downloaded enough from this journal
        if downloads_per_journal[journal] >= PDFS_PER_JOURNAL:
            continue

        attempted_per_journal[journal] += 1

        # Prepare filename using proper DOI encoding
        encoded_doi = encode_doi_for_filename(row['doi'])
        filename = f"{encoded_doi}.pdf"
        output_path = os.path.join(PDF_FOLDER, filename)

        print(f"\n[{downloads_successful + 1}/{TOTAL_PDFS}] {journal}")
        print(f"  DOI: {row['doi']}")

        # Download the PDF
        if download_pdf(row['oa_url'], output_path, i):
            row['downloaded'] = 'yes'
            downloads_successful += 1
            downloads_per_journal[journal] += 1

            # Save progress after each successful download
            write_csv(CSV_FILE, rows, fieldnames)

            # Be polite and wait a bit between downloads
            if downloads_successful < TOTAL_PDFS:
                time.sleep(1)
        else:
            # Mark as unavailable so we don't retry
            row['downloaded'] = 'unavailable'
            write_csv(CSV_FILE, rows, fieldnames)
            print(f"  Marked as unavailable, will not retry")

    print(f"\n{'='*60}")
    print(f"Download complete!")
    print(f"Successfully downloaded: {downloads_successful}/{TOTAL_PDFS} PDFs")
    print(f"Active journals used: {len(active_journals)} - {sorted(active_journals)}")
    print(f"Downloads per journal: {dict(downloads_per_journal)}")
    print(f"PDFs saved to: {PDF_FOLDER}/")
    print(f"CSV updated: {CSV_FILE}")

    if downloads_successful < TOTAL_PDFS:
        print(f"\nWARNING: Only {downloads_successful} PDFs were successfully downloaded.")
        print(f"Some downloads may have failed. Run the script again to retry.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
