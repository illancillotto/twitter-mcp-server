FROM python:3.11-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y gcc g++ make curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 twitter && mkdir -p /app/data /app/logs && chown -R twitter:twitter /app
WORKDIR /app
COPY --from=builder /root/.local /home/twitter/.local
COPY mcp_server/ ./mcp_server/
RUN chown -R twitter:twitter /app
USER twitter
ENV PATH=/home/twitter/.local/bin:$PATH PYTHONPATH=/app PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "-m", "uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "8000"]
