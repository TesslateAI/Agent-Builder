#!/bin/bash
# Temporary script to install SQLAlchemy in the running container

echo "Installing SQLAlchemy and psycopg2-binary..."
/opt/venv/bin/pip install SQLAlchemy==2.0.23 psycopg2-binary==2.9.9
echo "SQLAlchemy installation complete!"