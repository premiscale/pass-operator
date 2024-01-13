#! /usr/bin/env bash
# Start the pass operator after some initial SSH setup.


set -eo pipefail


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
mkdir ~/.ssh/
printf "%s" "$PASS_SSH_PRIVATE_KEY" > ~/.ssh/private-key
chmod 600 ~/.ssh/private-key
ssh-add ~/.ssh/private-key

# Import private gpg key for secrets' decryption.
mkdir ~/.gnupg
chmod 700 -R ~/.gnupg
echo "$PASS_GPG_KEY" | gpg --dearmor > ~/.gnupg/private-key
gpg --import ~/.gnupg/private-key

# Initialize pass with the indicated directory and GPG key ID to decrypt secrets pulled from the Git repository.
pass init --path="$PASS_DIRECTORY" "$PASS_GPG_KEY_ID"

# Start the operator, passing in arguments from K8s.
/tini -- passoperator "$@"