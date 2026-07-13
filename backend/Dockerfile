FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install LibreOffice Calc (用于 Excel 自动修复)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/* \
    && soffice --version

# Copy project files
COPY pyproject.toml .
COPY app/ app/

# Install dependencies
RUN uv sync --frozen

EXPOSE 8010

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
