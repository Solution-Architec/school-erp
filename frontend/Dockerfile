FROM node:22-alpine AS build
ARG VITE_ENABLE_DEMO_MODE=false
ARG VITE_DEMO_PASSWORD=
ENV VITE_ENABLE_DEMO_MODE=$VITE_ENABLE_DEMO_MODE
ENV VITE_DEMO_PASSWORD=$VITE_DEMO_PASSWORD
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
