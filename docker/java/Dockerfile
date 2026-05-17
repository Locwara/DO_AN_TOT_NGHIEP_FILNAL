FROM openjdk:17-slim

# Security: create a non-root user for running student code
RUN useradd -m -u 65534 sandbox

WORKDIR /sandbox
USER sandbox

CMD ["java"]
