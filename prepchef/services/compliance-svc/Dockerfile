FROM node:20-alpine AS base
WORKDIR /app

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

COPY --chown=nodejs:nodejs package*.json .
RUN npm ci --ignore-scripts
COPY --chown=nodejs:nodejs . .
RUN npm run build

# Switch to non-root user
USER nodejs

CMD ["node","dist/index.js"]
