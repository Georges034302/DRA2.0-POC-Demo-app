FROM nginx:alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx config
RUN rm /etc/nginx/nginx.conf

# Copy custom nginx config (will be processed by envsubst)
COPY nginx.conf /etc/nginx/nginx.conf.template

# Copy static files
COPY static /app/static

# Copy templates (for serving if needed)
COPY templates /app/templates

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Entrypoint to process envsubst and run nginx
CMD sh -c 'envsubst < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g "daemon off;"'
