# Node version for every stage. Defaults to the current LTS line; pin a
# specific major for reproducible builds with `--build-arg NODE_VERSION=26`.
ARG NODE_VERSION=lts

FROM node:${NODE_VERSION}-alpine AS base

# Stages that run pnpm. Node 25+ images no longer bundle corepack, so install it
# from npm. Corepack then reads the "packageManager" field in package.json and
# activates that exact pnpm version.
FROM base AS pnpm
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN npm install -g corepack@latest && corepack enable

FROM pnpm AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json pnpm-lock.yaml ./
# --frozen-lockfile fails the build if pnpm-lock.yaml is out of date
RUN pnpm install --frozen-lockfile

FROM pnpm AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm build

# Runtime stage only needs Node: Next's standalone output bundles its own
# minimal node_modules, so pnpm is not installed here.
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/package.json .
COPY --from=builder --chown=nextjs:nodejs /app/next.config.js ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT=3000

CMD ["node", "server.js"]
