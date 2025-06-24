FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .
EXPOSE 11434
CMD ["moogla", "serve"]
