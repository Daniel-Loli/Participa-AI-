# Stage 1: instalar solo dependencias de producción
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && \
    npm cache clean --force && \
    find node_modules -name "*.map" -delete && \
    find node_modules -name "*.md" -delete && \
    find node_modules -name "*.ts" -delete && \
    find node_modules -name "*.txt" -delete && \
    find node_modules -name "CHANGELOG*" -delete && \
    find node_modules -name "LICENSE*" -delete && \
    find node_modules -type d -name "test" -exec rm -rf {} + 2>/dev/null; \
    find node_modules -type d -name "__tests__" -exec rm -rf {} + 2>/dev/null; true

# Stage 2: compilar TypeScript
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 3: imagen de producción (distroless — sin shell, sin npm, superficie mínima)
FROM gcr.io/distroless/nodejs20-debian12 AS production
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["dist/main"]
