FROM node:22-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run typecheck && npm test

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
COPY package*.json ./
RUN npm ci --omit=dev
COPY --from=build /app/src ./src
COPY --from=build /app/tsconfig.json ./
RUN npm i -g tsx
# HTTP mode for deployment (no SLACK_APP_TOKEN → events over HTTP).
EXPOSE 3000
CMD ["tsx", "src/app.ts"]
