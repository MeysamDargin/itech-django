#!/bin/bash

# A script to update the Docker container with local changes

echo "Copying files to container..."

# Copy main app files
docker cp iTech itech-web-1:/app/
echo "✓ Copied iTech"

# Copy article app files
docker cp articles itech-web-1:/app/
echo "✓ Copied articles"

# Copy AI app files
docker cp ai itech-web-1:/app/
echo "✓ Copied ai"

docker cp report itech-web-1:/app/
echo "✓ Copied report"

docker cp search itech-web-1:/app/
echo "✓ Copied search"

docker cp notifications itech-web-1:/app/
echo "✓ Copied notifications"

docker cp otp itech-web-1:/app/
echo "✓ Copied otp"

docker cp comments itech-web-1:/app/
echo "✓ Copied comments"

docker cp config itech-web-1:/app/
echo "✓ Copied config"

docker cp feedback itech-web-1:/app/
echo "✓ Copied feedback"

docker cp emails itech-web-1:/app/
echo "✓ Copied emails"

docker cp following itech-web-1:/app/
echo "✓ Copied following"

docker cp profiles itech-web-1:/app/
echo "✓ Copied profiles"

docker cp temporalBehavior itech-web-1:/app/
echo "✓ Copied temporalBehavior"

docker cp accounts itech-web-1:/app/
echo "✓ Copied accounts"

# Fix permissions inside container
echo "Fixing permissions..."
docker exec itech-web-1 chmod -R 755 /app
echo "✓ Permissions fixed"

# Clear Python cache files
echo "Clearing Python cache..."
docker exec itech-web-1 find /app -name "*.pyc" -delete
docker exec itech-web-1 find /app -name "__pycache__" -exec rm -rf {} +
echo "✓ Python cache cleared"

# Touch the wsgi file to trigger reload
echo "Triggering app reload..."
docker exec itech-web-1 touch /app/iTech/wsgi.py
echo "✓ App reload triggered"

# Restart the web container
echo "Restarting web container..."
docker-compose restart web
echo "✓ Web container restarted"

# Wait for container to be up
echo "Waiting for container to be fully up..."
sleep 5

# Verify OTP utils file
echo "Verifying otp/utils.py content:"
docker exec itech-web-1 cat /app/otp/utils.py | grep -A 5 "if not settings.DEBUG"

echo "Container updated successfully!"