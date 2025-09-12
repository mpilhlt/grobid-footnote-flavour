#!/bin/bash

# Usage: ./unzip_all.sh <zip_directory> <output_base_directory>

# Check arguments
if [ "$#" -ne 2 ]; then
    echo "❌ Usage: $0 <zip_directory> <output_base_directory>"
    exit 1
fi

ZIP_DIR="$1"
OUTPUT_BASE="$2"

# Check if ZIP_DIR exists
if [ ! -d "$ZIP_DIR" ]; then
    echo "❌ Error: Zip directory '$ZIP_DIR' does not exist."
    exit 1
fi

# Create output base directory if it doesn't exist
mkdir -p "$OUTPUT_BASE"

# Loop through .zip files
find "$ZIP_DIR" -maxdepth 1 -name '*.zip' | while read -r zipfile; do
    filename=$(basename "$zipfile" .zip)
    output_dir="${OUTPUT_BASE}/${filename}"

    echo "📦 Unzipping '$zipfile' → '$output_dir'"

    mkdir -p "$output_dir"
    unzip -q "$zipfile" -d "$output_dir"
done

