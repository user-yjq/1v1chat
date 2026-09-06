# 1v1Chat frontend —— 构建产物 + nginx
# npm 默认走国内镜像（npmmirror，自动改写 lockfile 的 resolved 域名）；
# 海外/CI 覆盖：docker build --build-arg NPM_REGISTRY=https://registry.npmjs.org
FROM node:20-alpine AS builder

ARG NPM_REGISTRY=https://registry.npmmirror.com

WORKDIR /app
COPY package*.json ./
# 改写 lockfile resolved 域名到目标 registry 后 npm ci（仅构建层，不改源码锁文件）
RUN sed -i "s|https://registry\.npmjs\.org/|${NPM_REGISTRY}/|g" package-lock.json \
    && npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
