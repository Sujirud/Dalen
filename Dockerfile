FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd -m -r dalenuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY --chown=dalenuser:dalenuser . /app/

USER dalenuser

EXPOSE 8000

CMD ["gunicorn", "Dalen.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]