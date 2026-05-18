# Stage 1: Serve with Nginx on unprivileged port
FROM nginx:stable-alpine

# Copy the pre-built assets from the local build/ directory
# Note: Context should be the bs_frontend directory
COPY build/ /usr/share/nginx/html

# Copy a custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose unprivileged port 8080
EXPOSE 8080

# Default Nginx command
CMD ["nginx", "-g", "daemon off;"]
