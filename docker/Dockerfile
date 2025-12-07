FROM python:3.11-slim-bookworm

WORKDIR /app

# --- Install dependencies + precompiled Node.js ---
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        procps && \
    rm -rf /var/lib/apt/lists/*

# --- Install Python dependencies ---
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m ipykernel install --user

# --- Download Traefik static binary (v2.10.1) ---
COPY traefik.tar.gz /tmp/traefik.tar.gz
RUN tar -xzf /tmp/traefik.tar.gz -C /usr/local/bin/ traefik && \
    chmod +x /usr/local/bin/traefik && rm /tmp/traefik.tar.gz

# --- Setup Voila config ---
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

# --- Copy application code ---
COPY . .

# --- Copy Traefik config + scripts ---
COPY count_kernels.sh /app/count_kernels.sh
COPY dynamic_conf.yml /etc/traefik/dynamic_conf.yml
COPY traefik.yml /etc/traefik/traefik.yml
COPY run_voila.py /app/run_voila.py

RUN chmod +x /app/count_kernels.sh

EXPOSE 80

CMD ["sh", "-c", "\
    /app/count_kernels.sh & \
    python -m http.server 8867 --directory /tmp & \
    ( \
      python /app/run_voila.py > /dev/null 2>&1 & \
      echo 'Voila running at: http://localhost:8888' \
    ) & \
    python flask.py & \
    traefik --configFile=/etc/traefik/traefik.yml"]
