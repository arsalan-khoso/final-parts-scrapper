FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# Install dependencies for Google Chrome and Selenium
RUN apt-get update && \
    apt-get install -y \
    wget \
    curl \
    gnupg2 \
    unzip \
    libvulkan1 \
    libnss3 \
    libgdk-pixbuf2.0-0 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libnspr4 \
    libx11-xcb1 \
    libgbm1 \
    && \
    # Download and install Google Chrome stable version
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb && \
    # Clean up apt cache to free up space
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /var/cache/apt/archives/*

# Install ChromeDriver
RUN CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget -q https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip -d /usr/local/bin && \
    rm chromedriver_linux64.zip

# Set up the working directory
WORKDIR /app

# Copy requirements.txt first for better cache utilization
COPY requirements.txt /app/

# Install base Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir python-dotenv looseversion packaging gunicorn 

# Uninstall and reinstall undetected_chromedriver
RUN pip uninstall -y undetected-chromedriver && \
    pip install undetected-chromedriver==3.4.7

# Create fix_patcher.py
RUN echo '#!/usr/bin/env python3' > /app/fix_patcher.py && \
    echo 'import os' >> /app/fix_patcher.py && \
    echo 'import site' >> /app/fix_patcher.py && \
    echo 'import platform' >> /app/fix_patcher.py && \
    echo '' >> /app/fix_patcher.py && \
    echo 'def fix_patcher():' >> /app/fix_patcher.py && \
    echo '    # Find site-packages directory' >> /app/fix_patcher.py && \
    echo '    site_packages = [p for p in site.getsitepackages() if "site-packages" in p][0]' >> /app/fix_patcher.py && \
    echo '' >> /app/fix_patcher.py && \
    echo '    # Path to the patcher.py file' >> /app/fix_patcher.py && \
    echo '    patcher_path = os.path.join(site_packages, "undetected_chromedriver", "patcher.py")' >> /app/fix_patcher.py && \
    echo '' >> /app/fix_patcher.py && \
    echo '    if not os.path.exists(patcher_path):' >> /app/fix_patcher.py && \
    echo '        print(f"Patcher file not found at {patcher_path}")' >> /app/fix_patcher.py && \
    echo '        return' >> /app/fix_patcher.py && \
    echo '' >> /app/fix_patcher.py && \
    echo '    # Read the content of the file' >> /app/fix_patcher.py && \
    echo '    with open(patcher_path, "r") as f:' >> /app/fix_patcher.py && \
    echo '        content = f.read()' >> /app/fix_patcher.py && \
    echo '' >> /app/fix_patcher.py && \
    echo '    # Check if IS_POSIX is defined' >> /app/fix_patcher.py && \
    echo '    if "IS_POSIX = " not in content:' >> /app/fix_patcher.py && \
    echo '        # Add IS_POSIX definition' >> /app/fix_patcher.py && \
    echo '        content = "IS_POSIX = platform.system() in [\'Darwin\', \'Linux\']\\n" + content' >> /app/fix_patcher.py && \
    echo '' >> /app/fix_patcher.py && \
    echo '    # Fix the LooseVersion import' >> /app/fix_patcher.py && \
    echo '    if "from distutils.version import LooseVersion" in content:' >> /app/fix_patcher.py && \
    echo '        content = content.replace(' >> /app/fix_patcher.py && \
    echo '            "from distutils.version import LooseVersion",' >> /app/fix_patcher.py && \
    echo '            "try:\\n    from looseversion import LooseVersion\\nexcept ImportError:\\n    try:\\n        from distutils.version import LooseVersion\\n    except ImportError:\\n        from packaging.version import Version as LooseVersion"' >> /app/fix_patcher.py && \
    echo '        )' >> /app/fix_patcher.py && \
    echo '' >> /app/fix_patcher.py && \
    echo '    # Write the updated content back to the file' >> /app/fix_patcher.py && \
    echo '    with open(patcher_path, "w") as f:' >> /app/fix_patcher.py && \
    echo '        f.write(content)' >> /app/fix_patcher.py && \
    echo '' >> /app/fix_patcher.py && \
    echo '    print(f"Updated {patcher_path}")' >> /app/fix_patcher.py && \
    echo '' >> /app/fix_patcher.py && \
    echo 'if __name__ == "__main__":' >> /app/fix_patcher.py && \
    echo '    fix_patcher()' >> /app/fix_patcher.py

# Create init_db.py
RUN echo '#!/usr/bin/env python3' > /app/init_db.py && \
    echo 'from app import app, db, init_db' >> /app/init_db.py && \
    echo '' >> /app/init_db.py && \
    echo 'with app.app_context():' >> /app/init_db.py && \
    echo '    db.create_all()' >> /app/init_db.py && \
    echo '    init_db()' >> /app/init_db.py && \
    echo '    print("Database initialized successfully")' >> /app/init_db.py

# Make scripts executable
RUN chmod +x /app/fix_patcher.py /app/init_db.py

# Create the startup script
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'echo "Patching undetected_chromedriver..."' >> /app/start.sh && \
    echo 'python /app/fix_patcher.py' >> /app/start.sh && \
    echo 'echo "Initializing database..."' >> /app/start.sh && \
    echo 'python /app/init_db.py' >> /app/start.sh && \
    echo 'echo "Starting application..."' >> /app/start.sh && \
    echo 'gunicorn --bind 0.0.0.0:8080 --timeout 300 --workers 1 app:app' >> /app/start.sh && \
    chmod +x /app/start.sh

# Add a cleanup script
RUN echo '#!/bin/bash' > /app/cleanup.sh && \
    echo 'find /tmp -name "*chrome*" -type d -mmin +30 -exec rm -rf {} \; 2>/dev/null || true' >> /app/cleanup.sh && \
    echo 'pkill -f chrome 2>/dev/null || true' >> /app/cleanup.sh && \
    chmod +x /app/cleanup.sh

# Copy application files
COPY . /app/

# Make sure the SQLite database directory is writable
RUN mkdir -p /app/instance && chmod -R 777 /app

# Set environment variables for headless mode
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/google-chrome-stable

# Expose the port that your Flask app runs on
EXPOSE 8080

# Run the startup script
CMD ["/app/start.sh"]
