FROM node:22-bookworm-slim

RUN apt-get update \
  && apt-get install --no-install-recommends -y ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY midnight_service/package.json midnight_service/package-lock.json ./
RUN npm ci

COPY contract/verihire.compact /app/contract/verihire.compact
RUN curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/midnightntwrk/compact/releases/latest/download/compact-installer.sh \
  | sh \
  && /root/.local/bin/compact compile /app/contract/verihire.compact /app/managed/verihire

COPY midnight_service/ ./
RUN npm run build

ENV NODE_ENV=production
EXPOSE 7000
CMD ["node", "dist/server.js"]