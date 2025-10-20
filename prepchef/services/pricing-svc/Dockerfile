FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json .
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build
CMD ["node","dist/index.js"]
