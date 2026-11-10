FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt requirements.lock* ./
RUN if [ -f requirements.lock ]; then pip install -r requirements.lock; else pip install -r requirements.txt; fi

COPY . .

RUN useradd --create-home xpass && chown -R xpass /srv
USER xpass

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
