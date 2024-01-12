#! /usr/bin/env bash
# Start the pass operator after some initial SSH setup.

# Add private SSH key to the agent.
eval "$(ssh-agent -s)"
printf "%s" "$SSH_PRIVATE_KEY" > ~/.ssh/private-key
ssh-add ~/.ssh/private-key

# Import gpg key.
gpg --import "$GPG_KEY"

# Initialize pass with the indicated directory and GPG key ID to decrypt secrets pulled from the Git repository.
pass init --path="$PASS_DIRECTORY" "$GPG_KEY_ID"