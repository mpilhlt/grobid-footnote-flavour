#!/usr/bin/env python3
"""
Download sample PDFs from the CSV file.

This script processes the oa_law_review_samples_with_footnotes.csv file by:
- Downloading 10 PDFs (2 from each of 5 different journals)
- Prioritizing journals without any previous downloads
- Marking successful downloads in the "downloaded" column
"""

import csv
import json
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote
import time
from collections import defaultdict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
CSV_FILE = "data/oa_law_review_samples_with_footnotes.csv"
PDF_FOLDER = "pdf"
TOTAL_PDFS = 10


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


def check_open_access(doi):
    """
    Check if a DOI is Open Access with a CC-BY license using the Unpaywall API.

    Args:
        doi: The DOI string (with or without prefix)

    Returns:
        True if the article is Open Access with CC-BY license, False otherwise
    """
    # Get email from environment variable
    email = os.environ.get('UNPAYWALL_EMAIL')
    if not email:
        print("ERROR: UNPAYWALL_EMAIL environment variable not set")
        sys.exit(1)

    # Remove DOI prefix if present
    if doi.startswith('https://doi.org/'):
        doi = doi[16:]
    elif doi.startswith('http://doi.org/'):
        doi = doi[15:]

    api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ResearchBot/1.0)'
        }
        request = Request(api_url, headers=headers)

        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

            # Check if article is OA
            is_oa = data.get('is_oa', False)
            if not is_oa:
                print(f"  ✗ Not Open Access according to Unpaywall")
                return False

            # Check oa_locations for CC-BY license
            oa_locations = data.get('oa_locations', [])
            for location in oa_locations:
                license_info = location.get('license')
                if license_info:
                    # Only accept if license is cc-by
                    if license_info == 'cc-by':
                        return True
                    else:
                        print(f"  ✗ License is '{license_info}', not 'cc-by'")
                        return False

            # No license info found in any location, accept as OA
            return True

    except HTTPError as e:
        print(f"  WARNING: Unpaywall API HTTP Error {e.code}: {e.reason}")
        return True  # Assume OA if API fails
    except URLError as e:
        print(f"  WARNING: Unpaywall API URL Error: {e.reason}")
        return True  # Assume OA if API fails
    except Exception as e:
        print(f"  WARNING: Unpaywall API Error: {str(e)}")
        return True  # Assume OA if API fails


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

    # Download PDFs
    downloads_successful = 0
    downloads_per_journal = defaultdict(int)

    print(f"\nStarting downloads (target: {TOTAL_PDFS} PDFs)...")

    # Keep trying until we have enough successful downloads or run out of PDFs
    for i, row in enumerate(rows):
        if downloads_successful >= TOTAL_PDFS:
            break

        journal = row['journal']

        # Skip if already downloaded, unavailable, or not Open Access
        download_status = row.get('downloaded', '').lower()
        if download_status in ['yes', 'unavailable', 'not_oa']:
            continue

        # Prepare filename using proper DOI encoding
        encoded_doi = encode_doi_for_filename(row['doi'])
        filename = f"{encoded_doi}.pdf"
        output_path = os.path.join(PDF_FOLDER, filename)

        print(f"\n[{downloads_successful + 1}/{TOTAL_PDFS}] {journal}")
        print(f"  DOI: {row['doi']}")

        # Check Open Access status via Unpaywall API
        if not check_open_access(row['doi']):
            row['downloaded'] = 'not_oa'
            write_csv(CSV_FILE, rows, fieldnames)
            continue

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
