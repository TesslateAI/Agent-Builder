#!/bin/bash
# Quick script to rebuild frontend after changes

echo "🏗️  Rebuilding frontend..."
cd builder/frontend
npm run build
echo "✅ Frontend rebuilt successfully!"
echo "   Refresh your browser to see the changes"