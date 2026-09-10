FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install PyTorch CPU build first (lighter image), then PyG
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir torch-scatter torch-sparse torch-cluster torch-spline-conv \
    -f https://data.pyg.org/whl/torch-2.3.0+cpu.html
RUN pip install --no-cache-dir torch-geometric==2.5.3
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure runtime directories exist
RUN mkdir -p data/raw data/processed data/demo models/trained models/checkpoints

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
