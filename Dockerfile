FROM python:3.11-slim

# Set user with UID 1000 (standard for Hugging Face Spaces Docker)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Install Python dependencies
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=user:user . .

# Ensure storage directories are writable
RUN mkdir -p uploads && chmod -R 777 uploads && (test -f database.db && chmod 666 database.db || true)

USER user

# Hugging Face Spaces exposes port 7860
EXPOSE 7860

CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
