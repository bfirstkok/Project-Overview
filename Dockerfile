FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY . .
RUN useradd --create-home app && mkdir -p /app/media /app/staticfiles && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["sh", "entrypoint.sh"]
