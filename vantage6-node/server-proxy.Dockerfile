FROM ppdli-base
COPY /joey/local_proxy_server /app
EXPOSE 5001
ENTRYPOINT [ "python", "/app"]
