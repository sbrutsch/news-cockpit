FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/news-cockpit

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY public ./public

RUN useradd --system --home-dir /srv/news-cockpit appuser \
    && mkdir -p data && chown appuser data
USER appuser

ENV HOST=0.0.0.0 \
    PORT=8080
EXPOSE 8080

CMD ["python", "-m", "app.main"]
