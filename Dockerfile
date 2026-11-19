# WindGrid images. Two targets from one file:
#   docker build --target api -t windgrid-api .         -> dispatch API on :8000 (/docs)
#   docker build --target dashboard -t windgrid-dash .  -> Streamlit dashboard on :8501
# Or simply: docker compose up --build
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# LightGBM needs the OpenMP runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/windgrid
# Dependencies first, so code edits do not invalidate the dependency layer.
COPY pyproject.toml README.md LICENSE ./
COPY windgrid/__init__.py windgrid/__init__.py
RUN pip install --upgrade pip setuptools wheel
COPY windgrid ./windgrid
COPY publication_v2 ./publication_v2
RUN useradd --create-home --uid 10001 windgrid

FROM base AS api
RUN pip install ".[api]"
USER windgrid
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
CMD ["uvicorn", "windgrid.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

FROM base AS dashboard
RUN pip install ".[dashboard]"
COPY app ./app
COPY .streamlit ./.streamlit
COPY docs ./docs
USER windgrid
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4)"
CMD ["streamlit", "run", "app/dashboard.py", "--server.address", "0.0.0.0", "--server.port", "8501", "--server.headless", "true"]
