# -----------------------------------------------------------------------------
# Terminal Racing - Dockerfile
# Lightweight Python 3 Linux environment for interactive terminal racing.
# -----------------------------------------------------------------------------

# Step 1: Base Image (Official lightweight Python 3 on Debian Slim)
FROM python:3.12-slim

# Step 2: Environment Variables
# - PYTHONUNBUFFERED: Ensures standard output / stderr are delivered immediately to the terminal
# - TERM: Enables 256-color support in terminal emulators
# - LANG / LC_ALL: Ensures UTF-8 encoding support for ASCII borders and symbols
ENV PYTHONUNBUFFERED=1 \
    TERM=xterm-256color \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Step 3: Set working directory inside container
WORKDIR /app

# Step 4: Copy dependency definition and install (if any)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy application code
COPY game.py test_game.py /app/

# Step 6: Create a non-root user for security and grant permissions to /app
RUN useradd -m -u 1000 gamer && \
    chown -R gamer:gamer /app

USER gamer

# Step 7: Launch game automatically
CMD ["python", "game.py"]
