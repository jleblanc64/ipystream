FROM python:3.11-slim-bullseye

WORKDIR /app

# Install dependencies + tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    curl \
    build-essential \
    nodejs \
    npm && \
    rm -rf /var/lib/apt/lists/*

# Install python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m ipykernel install --user

# Download Traefik static binary (v2.10.1)
RUN curl -L -o /tmp/traefik.tar.gz https://github.com/traefik/traefik/releases/download/v2.10.1/traefik_v2.10.1_linux_amd64.tar.gz && \
    tar -xzf /tmp/traefik.tar.gz -C /usr/local/bin/ traefik && \
    chmod +x /usr/local/bin/traefik && rm /tmp/traefik.tar.gz

# Setup Voila config to allow websocket from Traefik on same host
RUN mkdir -p /etc/jupyter && \
    echo '{ \
      "VoilaConfiguration": { \
        "file_allowlist": [".*", "iframe_figures/.*"], \
        "show_tracebacks": true \
      }, \
      "ServerApp": { \
        "allow_origin": "*", \
        "allow_credentials": true, \
        "disable_check_xsrf": true, \
        "disable_check_trust": true \
      } \
    }' > /etc/jupyter/voila.json

# Copy application code
COPY . .

# Copy Traefik static config file (you create traefik.yml next)
COPY healthcheck/count_kernels.sh /app/count_kernels.sh
COPY healthcheck/dynamic_conf.yml /etc/traefik/dynamic_conf.yml
COPY healthcheck/traefik.yml /etc/traefik/traefik.yml
COPY run_voila.py /app/run_voila.py

# count_kernels
RUN chmod +x /app/count_kernels.sh

EXPOSE 80

CMD ["sh", "-c", "\
    /app/count_kernels.sh & \
    python -m http.server 8867 --directory /tmp & \
    ( \
      python /app/run_voila.py > /dev/null 2>&1 & \
      echo 'Voila running at: http://localhost:8888' \
    ) & \
    traefik --configFile=/etc/traefik/traefik.yml"]
