## Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: Apache-2.0

# Use the official Node.js image as the base
FROM node:20-alpine

# Install curl
RUN apk add --no-cache curl

# Set working directory
WORKDIR /app

# Copy app to image
COPY . ./

# Install dependencies
RUN npm install

# Expose the port that the app will run on
EXPOSE 8000
ENV SAMPLE_APP_PORT=8080
ENV SAMPLE_APP_ADDRESS=0.0.0.0

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Command to start the application
CMD ["npm", "run", "start"]