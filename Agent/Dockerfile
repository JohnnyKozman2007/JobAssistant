FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app/Agent

RUN pip install --no-cache-dir --upgrade pip uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port", "8888", "--no-browser", "--allow-root"]
