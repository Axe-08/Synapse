# Dockerfile for the Synapse Judge Environment

# Base image with GCC 12, which fully supports C++17, C++20, and C++23 standards.
FROM gcc:12

# Update package lists and install necessary command-line utilities.
# - coreutils: Provides the 'timeout' command for enforcing time limits on execution.
# - time: Provides the '/usr/bin/time' command for accurately measuring the wall-clock
#         execution time, which is essential for the VJS calibration logic.
# Using --no-install-recommends and cleaning up reduces final image size.
RUN apt-get update && apt-get install -y --no-install-recommends \
    coreutils \
    time \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container where code will be compiled and run.
WORKDIR /app