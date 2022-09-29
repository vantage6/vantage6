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

# When the container starts, replace the env.js with values from environment variables and then startup app
CMD ["/bin/sh",  "-c",  "envsubst < /usr/share/nginx/html/assets/env.template.js > /usr/share/nginx/html/assets/env.js && exec nginx -g 'daemon off;'"]