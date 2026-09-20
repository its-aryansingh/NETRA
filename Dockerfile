FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm install
COPY frontend/ ./
ENV NEXT_PUBLIC_DEMO=1
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app/frontend
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0

COPY --from=builder /app/frontend ./

EXPOSE 3000
CMD ["sh", "-c", "npx next start -H 0.0.0.0 -p ${PORT:-3000}"]

