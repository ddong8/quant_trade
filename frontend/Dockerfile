# frontend/Dockerfile

# --- Build Stage ---
FROM node:20-alpine as build-stage

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install
COPY frontend/. .
RUN npm run build

# --- Production Stage ---
FROM nginx:stable-alpine as production-stage

COPY --from=build-stage /app/dist /usr/share/nginx/html

# 如果需要，可以添加一个自定义的 nginx.conf
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
