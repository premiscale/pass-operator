#! /usr/bin/env bash
# Start the pass operator after some initial SSH setup.

if [ -z "$PASS_SSH_PRIVATE_KEY" ]; then
    printf "ERROR: PASS_SSH_PRIVATE_KEY is not defined. Please provide a valid private SSH key.\\n" >&2
    exit 1
fi

if [ -z "$PASS_GPG_KEY" ]; then
    printf "ERROR: PASS_GPG_KEY is not defined. Please provide a valid private GPG key.\\n" >&2
    exit 1
fi

if [ -z "$PASS_GPG_KEY_ID" ]; then
    printf "ERROR: PASS_GPG_KEY_ID is not defined. Please provide a valid private GPG key ID.\\n" >&2
    exit 1
fi

# Add private SSH key to SSH agent for git pulls.
eval "$(ssh-agent -s)"
printf "%s" "$PASS_SSH_PRIVATE_KEY" > ~/.ssh/private-key
ssh-add ~/.ssh/private-key

# Import private gpg key for secrets' decryption.
gpg --import <(printf "%s" "$PASS_GPG_KEY")

# Initialize pass with the indicated directory and GPG key ID to decrypt secrets pulled from the Git repository.
pass init --path="$PASS_DIRECTORY" "$PASS_GPG_KEY_ID"