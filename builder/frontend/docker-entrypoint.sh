#!/bin/sh
set -e

# Replace API_URL in the built files with actual backend URL
if [ ! -z "$API_URL" ]; then
    echo "Configuring API URL: $API_URL"
    find /usr/share/nginx/html -type f -name "*.js" -exec sed -i "s|http://localhost:5000|$API_URL|g" {} +
    find /usr/share/nginx/html -type f -name "*.html" -exec sed -i "s|http://localhost:5000|$API_URL|g" {} +
fi

# Execute the CMD
exec "$@"