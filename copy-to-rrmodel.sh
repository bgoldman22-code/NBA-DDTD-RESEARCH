#!/bin/bash
# Copy RRMODEL Integration Files
# Run this script from NBA-DDTD-RESEARCH directory

set -e  # Exit on error

echo "🚀 Copying NBA DD/TD Integration Files to RRMODEL..."
echo ""

# Check if RRMODEL directory exists
if [ ! -d "../RRMODEL" ]; then
    echo "❌ ERROR: RRMODEL directory not found at ../RRMODEL"
    echo "   Please update the RRMODEL_PATH variable in this script"
    exit 1
fi

# Set paths
RRMODEL_PATH="../RRMODEL"
SOURCE_PATH="./RRMODEL-files"

# Create directories in RRMODEL
echo "📁 Creating directories..."
mkdir -p "$RRMODEL_PATH/netlify/functions/_lib"
mkdir -p "$RRMODEL_PATH/src/components"

# Copy files
echo "📋 Copying blobs-nba.mjs..."
cp "$SOURCE_PATH/netlify/functions/_lib/blobs-nba.mjs" "$RRMODEL_PATH/netlify/functions/_lib/"

echo "📋 Copying nbaddtd-picks.mjs..."
cp "$SOURCE_PATH/netlify/functions/nbaddtd-picks.mjs" "$RRMODEL_PATH/netlify/functions/"

echo "📋 Copying NBADDTDPicks.jsx..."
cp "$SOURCE_PATH/src/components/NBADDTDPicks.jsx" "$RRMODEL_PATH/src/components/"

# Verify files copied
echo ""
echo "✅ Verifying files..."
if [ -f "$RRMODEL_PATH/netlify/functions/_lib/blobs-nba.mjs" ]; then
    echo "   ✓ blobs-nba.mjs"
else
    echo "   ✗ blobs-nba.mjs FAILED"
fi

if [ -f "$RRMODEL_PATH/netlify/functions/nbaddtd-picks.mjs" ]; then
    echo "   ✓ nbaddtd-picks.mjs"
else
    echo "   ✗ nbaddtd-picks.mjs FAILED"
fi

if [ -f "$RRMODEL_PATH/src/components/NBADDTDPicks.jsx" ]; then
    echo "   ✓ NBADDTDPicks.jsx"
else
    echo "   ✗ NBADDTDPicks.jsx FAILED"
fi

echo ""
echo "🎉 Files copied successfully!"
echo ""
echo "⚠️  NEXT STEPS:"
echo "   1. Edit netlify/functions/nbaddtd-picks.mjs line 11"
echo "      Replace: YOUR_GITHUB_USERNAME"
echo "   2. Edit src/pages/NBA.jsx"
echo "      Add import: import NBADDTDPicks from '../components/NBADDTDPicks';"
echo "      Add component: <NBADDTDPicks />"
echo "   3. Run: cd $RRMODEL_PATH && npm install @netlify/blobs @netlify/functions"
echo ""
