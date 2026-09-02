#!/bin/bash
# download_reference_pack.sh - Download and verify private reference pack
#
# Downloads the private reference pack from a secure location and verifies
# its integrity using SHA-256 checksums from reference.json.
#
# Required environment variables:
#   REFERENCE_PACK_SOURCE: URL or absolute path to the reference pack (.tar.gz)
#   REFERENCE_PACK_DIR: Directory where to extract the pack
#
# Optional environment variables:
#   REFERENCE_PACK_TOKEN: Token for authenticated access (if needed)
#
# Exit codes:
#   0 = Success
#   1 = Configuration error
#   2 = Download failed
#   3 = Verification failed

set -euo pipefail

echo "=== Downloading reference pack ==="

# Validate required variables
if [ -z "${REFERENCE_PACK_SOURCE:-}" ]; then
    echo "ERROR: REFERENCE_PACK_SOURCE not set" >&2
    echo "Set REFERENCE_PACK_SOURCE to the URL or absolute path of the reference pack" >&2
    exit 1
fi

if [ -z "${REFERENCE_PACK_DIR:-}" ]; then
    echo "ERROR: REFERENCE_PACK_DIR not set" >&2
    echo "Set REFERENCE_PACK_DIR to the directory where to extract the pack" >&2
    exit 1
fi

# Create directory
mkdir -p "$REFERENCE_PACK_DIR"

echo "Source: $REFERENCE_PACK_SOURCE"
echo "Target: $REFERENCE_PACK_DIR"

# Download or copy reference pack
if [[ "$REFERENCE_PACK_SOURCE" =~ ^https?:// ]]; then
    # HTTP download
    if [ -n "${REFERENCE_PACK_TOKEN:-}" ]; then
        echo "Using authenticated download"
        if ! curl -sSL -H "Authorization: Bearer $REFERENCE_PACK_TOKEN" \
             "$REFERENCE_PACK_SOURCE" -o "$REFERENCE_PACK_DIR/reference-pack.tar.gz"; then
            echo "ERROR: Download failed" >&2
            exit 2
        fi
    else
        echo "Using public download"
        if ! curl -sSL "$REFERENCE_PACK_SOURCE" -o "$REFERENCE_PACK_DIR/reference-pack.tar.gz"; then
            echo "ERROR: Download failed" >&2
            exit 2
        fi
    fi
    
    # Extract
    tar -xzf "$REFERENCE_PACK_DIR/reference-pack.tar.gz" -C "$REFERENCE_PACK_DIR"
    rm -f "$REFERENCE_PACK_DIR/reference-pack.tar.gz"
    
elif [[ "$REFERENCE_PACK_SOURCE" =~ ^/ ]]; then
    # Local path
    if [ ! -f "$REFERENCE_PACK_SOURCE" ]; then
        echo "ERROR: Local reference pack not found: $REFERENCE_PACK_SOURCE" >&2
        exit 2
    fi
    
    tar -xzf "$REFERENCE_PACK_SOURCE" -C "$REFERENCE_PACK_DIR"
else
    echo "ERROR: Invalid REFERENCE_PACK_SOURCE format" >&2
    echo "Must be a URL (http:// or https://) or absolute path" >&2
    exit 1
fi

# Verify required files exist
echo "Verifying reference pack contents..."

required_files=(
    "$REFERENCE_PACK_DIR/main.elf"
    "$REFERENCE_PACK_DIR/switch_symbols.txt"
    "$REFERENCE_PACK_DIR/reference.json"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: Required file missing: $file" >&2
        exit 3
    fi
done

# Load expected SHA-256 from reference.json
echo "Loading expected checksums from reference.json..."

EXPECTED_ELF_SHA=$(python3 -c "import json; print(json.load(open('$REFERENCE_PACK_DIR/reference.json'))['main_elf_sha256'])")
EXPECTED_SYMBOLS_SHA=$(python3 -c "import json; print(json.load(open('$REFERENCE_PACK_DIR/reference.json'))['switch_symbols_sha256'])")

# Calculate actual SHA-256
ACTUAL_ELF_SHA=$(sha256sum "$REFERENCE_PACK_DIR/main.elf" | cut -d' ' -f1)
ACTUAL_SYMBOLS_SHA=$(sha256sum "$REFERENCE_PACK_DIR/switch_symbols.txt" | cut -d' ' -f1)

# Verify checksums
if [ "$ACTUAL_ELF_SHA" != "$EXPECTED_ELF_SHA" ]; then
    echo "ERROR: main.elf SHA-256 mismatch" >&2
    echo "Expected: $EXPECTED_ELF_SHA" >&2
    echo "Actual:   $ACTUAL_ELF_SHA" >&2
    exit 3
fi

if [ "$ACTUAL_SYMBOLS_SHA" != "$EXPECTED_SYMBOLS_SHA" ]; then
    echo "ERROR: switch_symbols.txt SHA-256 mismatch" >&2
    echo "Expected: $EXPECTED_SYMBOLS_SHA" >&2
    echo "Actual:   $ACTUAL_SYMBOLS_SHA" >&2
    exit 3
fi

echo "✅ Reference pack verified successfully"
echo "   main.elf SHA-256: $ACTUAL_ELF_SHA"
echo "   switch_symbols.txt SHA-256: $ACTUAL_SYMBOLS_SHA"

# Export checksums for use in workflow (GitHub Actions compatible)
if [ -n "${GITHUB_ENV:-}" ]; then
    echo "REFERENCE_ELF_SHA256=$ACTUAL_ELF_SHA" >> "$GITHUB_ENV"
    echo "REFERENCE_SYMBOLS_SHA256=$ACTUAL_SYMBOLS_SHA" >> "$GITHUB_ENV"
else
    # Fallback for local testing
    export REFERENCE_ELF_SHA256="$ACTUAL_ELF_SHA"
    export REFERENCE_SYMBOLS_SHA256="$ACTUAL_SYMBOLS_SHA"
fi

exit 0
