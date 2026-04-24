# Stage 1: Build Vue dashboard
FROM node:20-alpine AS frontend-builder
WORKDIR /dashboard
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm ci
COPY dashboard/ .
RUN npm run build
# Output: /dashboard/../server/static → /server/static
# vite.config.js sets outDir: '../server/static', so output is at /server/static

# Stage 2: Python server
FROM python:3.12-slim

WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ .

# Copy built frontend from stage 1
COPY --from=frontend-builder /server/static ./static

EXPOSE 8080 2200-2299/tcp 2200-2299/udp

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
