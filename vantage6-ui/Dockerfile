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