# Render entrypoint for the asked-and-answered service.
# The service rootDir is empty, so the build context is the repo root;
# this Dockerfile delegates to the asked-and-answered/ subdirectory.
FROM node:22-slim AS build
WORKDIR /app
RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*
COPY asked-and-answered/package*.json ./
RUN npm ci
COPY asked-and-answered/. .
RUN npm run typecheck && npm test

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*
COPY asked-and-answered/package*.json ./
RUN npm ci --omit=dev
COPY --from=build /app/src ./src
COPY --from=build /app/scripts ./scripts
COPY --from=build /app/tsconfig.json ./
COPY --from=build /app/public ./public
COPY --from=build /app/slack ./slack
COPY --from=build /app/docs ./docs
RUN npm i -g tsx
EXPOSE 3000
CMD ["tsx", "src/app.ts"]
