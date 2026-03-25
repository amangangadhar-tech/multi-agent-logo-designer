FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libcairo2 libpango-1.0-0 libffi-dev libgdk-pixbuf2.0-0 \
    libpangoft2-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
