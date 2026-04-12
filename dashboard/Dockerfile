FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

# 构建产物在 ../server/static，由 server 容器托管，此镜像仅用于构建
