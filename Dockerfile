FROM ubuntu:latest

 # 1. Prevent interactive prompts during package install
 # 2. Prevent buffering of stdout and stderr for immediate logs
 # 3. Prevent writing bytecode to disk to keep container clean
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        curl \
        ca-certificates \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy the app source
WORKDIR /app
COPY . .

# Install dependencies
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin:${PATH}"
RUN uv sync
ENV PATH="/app/.venv/bin:${PATH}"

# Remove default nginx site
RUN rm /etc/nginx/sites-enabled/default

# Copy the nginx configuration
COPY src/aspis/nginx/nginx.conf /etc/nginx/nginx.conf

RUN chmod +x docker_services.sh

EXPOSE 8080

CMD ["./docker_services.sh"]
