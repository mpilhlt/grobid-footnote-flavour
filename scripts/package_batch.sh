#!/bin/bash

# Packaging script for batch processing
#
# Usage: ./package_batch.sh <batch_directory>
#
# This script takes a batch directory as input and:
# 1. Discovers all model types from .tei.xml files
# 2. Creates a new directory called 4_packaging
# 3. Creates subdirectories for each model type with tei/ and raw/ subdirs
# 4. Copies files organized by model type to their respective tei/raw directories
#
# If 2_collected directories are not found, it will look in 1_generated and 2_corrected directories.

set -e  # Exit on any error

# Function to display usage
usage() {
    echo "Usage: $0 <batch_directory>"
    echo "Example: $0 batches/batch_1"
    exit 1
}

# Check if argument is provided
if [ $# -ne 1 ]; then
    usage
fi

BATCH_DIR="$1"

# Check if batch directory exists
if [ ! -d "$BATCH_DIR" ]; then
    echo "Error: Batch directory '$BATCH_DIR' does not exist."
    exit 1
fi

# Get absolute path
BATCH_DIR=$(realpath "$BATCH_DIR")
PACKAGING_DIR="$BATCH_DIR/4_packaging"

echo "Processing batch directory: $BATCH_DIR"

# Function to discover model types
discover_models() {
    local search_dirs=("$@")
    local models=()

    for search_dir in "${search_dirs[@]}"; do
        if [ -d "$search_dir" ]; then
            # Extract model names from .tei.xml files
            for tei_file in "$search_dir"/*/*.tei.xml; do
                if [ -f "$tei_file" ]; then
                    # Extract model name from filename like: doc.training.segmentation.tei.xml -> segmentation
                    model_name=$(basename "$tei_file" | sed 's/.*\.\(.*\)\.tei\.xml/\1/')
                    models+=("$model_name")
                fi
            done
        fi
    done

    # Get unique model names
    printf '%s\n' "${models[@]}" | sort -u
}

# Function to create model directories
create_model_directories() {
    local models=("$@")

    echo "Creating model directories..."

    for model in "${models[@]}"; do
        local model_dir="$PACKAGING_DIR/$model"
        local tei_dir="$model_dir/tei"
        local raw_dir="$model_dir/raw"

        mkdir -p "$tei_dir" "$raw_dir"
        echo "Created: $model_dir/ with tei/ and raw/ subdirectories"
    done
}

# Function to copy files by model
copy_files_by_model() {
    local search_dirs=("$@")
    local total_tei=0
    local total_seg=0

    echo "Organizing files by model type..."

    for search_dir in "${search_dirs[@]}"; do
        if [ -d "$search_dir" ]; then
            echo "Processing files in: $search_dir"

            # Process TEI files
            for tei_file in "$search_dir"/*/*.tei.xml; do
                if [ -f "$tei_file" ]; then
                    # Extract model name
                    model_name=$(basename "$tei_file" | sed 's/.*\.\(.*\)\.tei\.xml/\1/')
                    tei_dir="$PACKAGING_DIR/$model_name/tei"

                    if [ -d "$tei_dir" ]; then
                        cp "$tei_file" "$tei_dir/"
                        echo "  Copied TEI file: $(basename "$tei_file") -> $model_name/tei/"
                        ((total_tei++))
                    fi
                fi
            done

            # Process segmentation files - all go to segmentation/raw
            for seg_file in "$search_dir"/*/*.segmentation; do
                if [ -f "$seg_file" ]; then
                    raw_dir="$PACKAGING_DIR/segmentation/raw"

                    if [ -d "$raw_dir" ]; then
                        cp "$seg_file" "$raw_dir/"
                        echo "  Copied segmentation file: $(basename "$seg_file") -> segmentation/raw/"
                        ((total_seg++))
                    fi
                fi
            done
        fi
    done

    echo "Total TEI files copied: $total_tei"
    echo "Total segmentation files copied: $total_seg"
}

# Remove existing packaging directory if it exists
if [ -d "$PACKAGING_DIR" ]; then
    echo "Removing existing directory: $PACKAGING_DIR"
    rm -rf "$PACKAGING_DIR"
fi

# Look for 2_collected directories first
if [ -d "$BATCH_DIR/2_collected" ]; then
    echo "Found 2_collected directory"
    search_dirs=("$BATCH_DIR"/2_collected)
else
    # Only use 2_corrected directory
    if [ -d "$BATCH_DIR/2_corrected" ]; then
        echo "Using 2_corrected directory"
        search_dirs=("$BATCH_DIR"/2_corrected)
    else
        echo "Error: Neither 2_collected nor 2_corrected directories found."
        exit 1
    fi
fi

# Discover model types
echo "Discovering model types..."
models=($(discover_models "${search_dirs[@]}"))

if [ ${#models[@]} -eq 0 ]; then
    echo "Error: No model types found in the batch directory."
    exit 1
fi

echo "Found model types: ${models[*]}"

# Create packaging directory structure
mkdir -p "$PACKAGING_DIR"
echo "Created packaging directory: $PACKAGING_DIR"

# Create model-specific directories
create_model_directories "${models[@]}"

# Copy files organized by model
copy_files_by_model "${search_dirs[@]}"

echo ""
echo "Packaging complete!"
echo "Files organized by model type in: $PACKAGING_DIR"

# Display summary
for model in "${models[@]}"; do
    tei_count=$(find "$PACKAGING_DIR/$model/tei" -name "*.tei.xml" 2>/dev/null | wc -l)
    seg_count=$(find "$PACKAGING_DIR/$model/raw" -name "*.$model" 2>/dev/null | wc -l)
    echo "  $model: $tei_count TEI files, $seg_count $model files"
done

exit 0