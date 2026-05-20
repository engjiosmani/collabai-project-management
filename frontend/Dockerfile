# Step 1: Build the React application
FROM node:20-alpine AS build
WORKDIR /app

# Copy package configurations and install dependencies
COPY package*.json ./
RUN npm install

# Copy source code and build the production bundle
COPY . .
RUN npm run build

# Step 2: Serve the build folder using a lightweight Nginx web server
FROM nginx:stable-alpine
COPY --from=build /app/build /usr/share/nginx/html

# Expose HTTP port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
