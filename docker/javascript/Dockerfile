FROM node:20-alpine

# Install GNU time for memory measurement
RUN apk add --no-cache time

# Security: create a non-root user for running student code
RUN adduser -D -u 65534 sandbox

WORKDIR /sandbox
USER sandbox

CMD ["node"]
