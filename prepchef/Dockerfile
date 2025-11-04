FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Expose Node API port
EXPOSE 3000

# Start the application
CMD ["npm", "run", "dev"]
