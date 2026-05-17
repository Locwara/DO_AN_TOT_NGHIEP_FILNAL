FROM gcc:13-bookworm

# Security: create a non-root user for running student code
RUN useradd -m -u 65534 sandbox

# g++ is already included in the gcc image
# Keep the image minimal

WORKDIR /sandbox
USER sandbox

CMD ["/bin/bash"]
