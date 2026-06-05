FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "sqlalchemy>=2.0.30" "psycopg2-binary>=2.9.9" "pydantic>=2.7.0" \
    "python-dotenv>=1.0.1" "feedparser>=6.0.11" "requests>=2.32.0" \
    "beautifulsoup4>=4.12.3" "markdownify>=0.12.1" "openai>=1.40.0" \
    "youtube-transcript-api>=0.6.2" "google-api-python-client>=2.130.0" \
    "tenacity>=8.4.0" "jinja2>=3.1.4"

COPY . .

CMD ["python", "main.py"]
