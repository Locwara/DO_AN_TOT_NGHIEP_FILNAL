FROM openjdk:17-slim

# Install GNU time for memory measurement
RUN apt-get update && apt-get install -y time && rm -rf /var/lib/apt/lists/*

# Security: create a non-root user for running student code
RUN useradd -m -u 65534 sandbox

WORKDIR /sandbox
USER sandbox

CMD ["java"]
