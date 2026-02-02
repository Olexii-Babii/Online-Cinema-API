#!/bin/bash

# Check if MailHog user and password are set
if [ -n "$MAIL_USERNAME" ] && [ -n "$MAIL_PASSWORD" ]; then
  # Generate bcrypt-hashed password
  HASHED_PASSWORD=$(MailHog bcrypt "$MAIL_PASSWORD")

  # Create authentication file with username and hashed password
  echo "$MAIL_USERNAME:$HASHED_PASSWORD" > /mailhog.auth
  echo "Auth file created with user: $MAIL_USERNAME and hashed password."
else
  echo "MAIL_USERNAME or MAIL_PASSWORD not set. Auth file not created."
fi