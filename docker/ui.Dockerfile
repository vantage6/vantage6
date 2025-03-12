ARG TAG=latest
FROM node:20-alpine as node

LABEL version=${TAG}
LABEL maintainer="Bart van Beusekom <b.vanbeusekom@iknl.nl>, Frank Martin <f.martin@iknl.nl>"

# copy and install
WORKDIR /app
COPY vantage6-ui/ /app
RUN npm install
RUN npm run build

# run
FROM nginx:alpine
COPY --from=node /app/startup /app/startup
COPY --from=node /app/dist/vantage6-UI /usr/share/nginx/html

# Copy nginx config file to container
COPY vantage6-ui/nginx.conf /etc/nginx/nginx.conf

RUN chmod +x /app/startup/replace_env_vars.sh

# When the container starts, replace the env.js with values from environment variables and then startup app
CMD ["/bin/sh",  "-c",  "/app/startup/replace_env_vars.sh && exec nginx -g 'daemon off;'"]