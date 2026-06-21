FROM mono:6.12
# Install GNU time for memory measurement
RUN apt-get update && apt-get install -y time && rm -rf /var/lib/apt/lists/*

WORKDIR /sandbox
# The environment is already set up by the mono image.
# We will use 'mcs' to compile and 'mono' to run.
