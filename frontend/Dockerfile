# syntax=docker/dockerfile:1.7
#
# Next.js frontend image. Uses `output: "standalone"` (set in next.config.js)
# so the final stage can copy a pre-bundled server with no node_modules.
#
# Build args let us pass the Google client id and backend URL at build time
# so they're baked into the JS bundle.
#
# Stages:
#   1. deps      — installs the full dependency tree
#   2. builder   — runs `next build` with the standalone output
#   3. runner    — copies only the standalone server + static assets

ARG NODE_VERSION=20-alpine

# ---------------------------------------------------------------------------
# 1. Install dependencies
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION} AS deps
WORKDIR /app

# Copy lockfile + manifests first for better layer caching.
COPY package.json package-lock.json* ./
RUN \
  if [ -f package-lock.json ]; then npm ci; \
  else echo "Lockfile not found, falling back to npm install" && npm install; \
  fi

# ---------------------------------------------------------------------------
# 2. Build
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION} AS builder
WORKDIR /app

# Public build-time env vars.
ARG NEXT_PUBLIC_BACKEND_URL=""
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID=""
ENV NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL} \
    NEXT_PUBLIC_GOOGLE_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_CLIENT_ID} \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN mkdir -p public
RUN npm run build

# ---------------------------------------------------------------------------
# 3. Production runner
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION} AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Non-root user. node-alpine ships with `node` (uid 1000).
RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

# `next.config.js` enables `output: "standalone"`, which writes a minimal
# server.js plus a trace of the needed node_modules under .next/standalone.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static       ./.next/static
# Public/ is optional — copy only if it exists.
COPY --from=builder --chown=nextjs:nodejs /app/public              ./public

USER nextjs

EXPOSE 3000

# The standalone server boots on $PORT (default 3000).
CMD ["node", "server.js"]
