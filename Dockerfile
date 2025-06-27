FROM python:3.11-slim AS builder
WORKDIR /build

# Install runtime dependencies
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
EXPOSE 11434
CMD ["moogla", "serve"]
