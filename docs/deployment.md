# Deployment

This page outlines options for running Moogla in containers and how to secure a production instance.

## Docker

Build and start the server using the provided image:

```bash
docker build -t moogla .
docker run -p 11434:11434 moogla
```

Compose can mount a models directory and provide environment variables:

```bash
docker-compose up
```

## Kubernetes

Create a deployment using the Docker image and expose port `11434` via a
service. Models can be mounted from a persistent volume claim and
configuration values passed as environment variables or a secret.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: moogla
spec:
  replicas: 1
  selector:
    matchLabels:
      app: moogla
  template:
    metadata:
      labels:
        app: moogla
    spec:
      containers:
      - name: moogla
        image: moogla:latest
        ports:
        - containerPort: 11434
```

## HTTPS Setup

Run Moogla behind a reverse proxy such as Nginx or Traefik. Terminate TLS
at the proxy and forward requests to the application. Ensure ports `80`
and `443` are open for HTTP and HTTPS traffic.

## Environment Variables

Sensitive configuration like API keys should be set with environment
variables. In Docker or Kubernetes you can load a file with `--env-file`
or reference a secret:

```bash
docker run --env-file .env moogla
```

```yaml
env:
  - name: MOOGLA_API_KEY
    valueFrom:
      secretKeyRef:
        name: moogla-secrets
        key: api-key
```

## Security Best Practices

- Restrict access to the API with authentication and rate limiting.
- Keep dependencies updated and rebuild images when new versions are
  released.
- Limit network exposure by running the server behind a proxy and only
  exposing required ports.
