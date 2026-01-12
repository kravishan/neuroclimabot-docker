# Multi-stage build for React + Vite application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application files
COPY . .

# Accept build arguments for Vite environment variables
ARG VITE_API_BASE_URL
ARG VITE_API_DOCUMENT_URL
ARG VITE_TRANSLATE_API_URL
ARG VITE_STP_SERVICE_URL

# Set environment variables for the build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_DOCUMENT_URL=${VITE_API_DOCUMENT_URL}
ENV VITE_TRANSLATE_API_URL=${VITE_TRANSLATE_API_URL}
ENV VITE_STP_SERVICE_URL=${VITE_STP_SERVICE_URL}

# Build the application with environment variables
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
