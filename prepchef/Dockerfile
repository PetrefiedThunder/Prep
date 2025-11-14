FROM node:20-alpine

WORKDIR /app

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

# Copy package files
COPY --chown=nodejs:nodejs package*.json ./

# Install dependencies (production only)
RUN npm ci --omit=dev

# Copy application code
COPY --chown=nodejs:nodejs . .

# Build the application for production
RUN npm run build

# Switch to non-root user
USER nodejs

# Expose Node API port
EXPOSE 3000

# Start the application in production mode
CMD ["npm", "run", "start"]
