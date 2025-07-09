# This docker file is used solely for the development of the UI. It is not used in the
# production environment. The difference with the production docker file is that this
# file does not build the UI, but only serves it. This is done to allow for hot
# reloading of the UI code when developing, which is not possible after the compilation
# that is done for production.
ARG TAG=latest
FROM node:alpine

LABEL version=${TAG}
LABEL maintainer="Bart van Beusekom <b.vanbeusekom@iknl.nl>, Frank Martin <f.martin@iknl.nl>"

# Install gettext for envsubst command
RUN apk add --no-cache gettext

RUN npm install -g @angular/cli

# copy and install
WORKDIR /app
COPY vantage6-ui/ /app
RUN npm install

RUN chmod +x /app/startup/dev_startup.sh

CMD ["/bin/sh", "/app/startup/dev_startup.sh"]
