FROM node:16 as node

LABEL maintainer="Bart van Beusekom <b.vanbeusekom@iknl.nl>, Frank Martin <f.martin@iknl.nl>"

# copy and install
WORKDIR /app
COPY . /app
RUN npm install
RUN npm run build --prod

# run
FROM nginx:alpine
COPY --from=node /app/dist/vantage6-UI /usr/share/nginx/html


# add option to not share server info to nginx config file. Be sure to do this
# in the http block, which is achieved by matching that line
RUN sed -i '/http {/a \ \ \ \ server_tokens off;' /etc/nginx/nginx.conf

# When the container starts, replace the env.js with values from environment variables and then startup app
CMD ["/bin/sh",  "-c",  "envsubst < /usr/share/nginx/html/assets/env.template.js > /usr/share/nginx/html/assets/env.js && exec nginx -g 'daemon off;'"]