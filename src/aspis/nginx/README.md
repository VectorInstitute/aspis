# Running Aspis behind NGINX

In certain situations, we would want Aspis to run bexind a reverse proxy
so the UI and the API can run under the same address and port.

We chose NGINX as the reverse proxy and below are the instructions on how to
set it up.

## Installing NGINX

If you're running on Windows, follow this guide:
https://nginx.org/en/docs/windows.html

If you're running on Linux or MacOS, follow this guide:
https://docs.nginx.com/nginx/admin-guide/installing-nginx/installing-nginx-open-source/


## Copy the configuration

The configuration under the [`nginx.conf` file](nginx.conf) will configure
NGINX appropriately. Copy it to the NGINX config directory, the location of
such directory will depend on your operating system. For example, on MacOS
that directory is the following

```bash
cp nginx.conf /opt/homebrew/etc/nginx
```

## Running NGINX:

Running NGINX will also depend on your operating system. On MacOS, the
command to start NGINX is the following:

```bash
brew services start nginx
```

## Start the UI and the API:

After configuring the app from the main [README.md](../../../README.md) file,
you can start both services with the following commands:

```bash
streamlit run src/aspis/ui/main.py
```

```bash
fastapi dev src/aspis/api/main.py --forwarded-allow-ips="*" --proxy-headers --root-path /api
```


## Accessing the API and the UI

After everything is started, you can access the UI at the following address:

```bash
http://localhost:8080
```

The API endpoints will be available under `/api`. For example:

```bash
http://localhost:8080/api/test
```

The API docs will be available at:

```bash
http://localhost:8080/api/docs
```
