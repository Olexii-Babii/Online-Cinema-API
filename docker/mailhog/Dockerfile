FROM golang:1.24-bookworm

# Install necessary dependencies
RUN apt update && apt install -y  \
    wget \
    dos2unix \
    git \
    && apt clean

# Install MailHog
RUN go install github.com/mailhog/MailHog@latest

# Verify installation and create symlink for easier access
RUN ls -la /go/bin/ && ln -s /go/bin/MailHog /usr/local/bin/MailHog

# Copy the commands directory into the container
COPY commands/setup_mailhog_auth.sh /commands/setup_mailhog_auth.sh

# Ensure all scripts have Unix-style line endings and are executable
RUN dos2unix /commands/setup_mailhog_auth.sh && chmod +x /commands/setup_mailhog_auth.sh

# Expose MailHog ports
EXPOSE 1025 8025

# Default working directory
WORKDIR /app