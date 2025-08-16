# Dockerfile for the Synapse Judge Environment
FROM gcc:12
# Install essentials, 'timeout' is part of coreutils
RUN apt-get update && apt-get install -y coreutils
WORKDIR /app