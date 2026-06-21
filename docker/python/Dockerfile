FROM python:3.11-alpine

# Install GNU time for memory measurement
RUN apk add --no-cache time

# Security: create a non-root user for running student code
RUN adduser -D -u 65534 sandbox

# No extra packages needed – Python is included in the base image
# Keep the image as small as possible for fast container starts

WORKDIR /sandbox
USER sandbox

# Default entrypoint – overridden by docker run command
CMD ["python3"]
