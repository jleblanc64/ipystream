#!/bin/bash

REPO="jleblanc64/ipystream"
BRANCH="main"
FOLDER="docker"
OUT_DIR="docker"

mkdir -p "$OUT_DIR"

# Query GitHub API for folder contents
curl -s "https://api.github.com/repos/$REPO/contents/$FOLDER?ref=$BRANCH" \
  | jq -r '.[] | select(.type=="file") | .download_url' \
  | while read url; do
        filename="$(basename "$url")"
        outpath="$OUT_DIR/$filename"

        # Skip if file is traefik.tar.gz and already exists
        if ( [ "$filename" = "traefik.tar.gz" ] || [ "$filename" = "flask_app.py" ] ) && [ -f "$outpath" ]; then
            echo "Skipping $filename (already exists)"
            continue
        fi

        echo "Downloading $url"
        curl -L "$url" -o "$outpath"
    done

echo "Done."

mkdir docker/.git
cp -r python docker
cp run_voila.py docker/
cp requirements.txt docker/
docker build -t app_cars docker

# optional: kill previously started app
docker ps --filter "publish=8888" -q | xargs -r docker stop \
 && docker ps -a --filter "publish=8888" -q | xargs -r docker rm

docker run -p 8888:80 app_cars