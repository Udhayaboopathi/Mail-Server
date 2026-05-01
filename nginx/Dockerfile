FROM nginx:1.27-alpine

RUN apk add --no-cache certbot certbot-nginx

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
