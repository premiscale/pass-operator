#! /usr/bin/env bash
# Initialize the operator e2e git repository with initial data and branches.


set -o pipefail


if [ -z "$SSH_PRIVATE_KEY" ]; then
    printf "ERROR: SSH_PUBLIC_KEY is not defined. Please provide a valid private SSH key.\\n" >&2
    exit 1
fi

if [ -z "$PASS_GPG_KEY" ]; then
    printf "ERROR: PASS_GPG_KEY is not defined. Please provide a valid public GPG key for encryption.\\n" >&2
    exit 1
fi

if [ -z "$PASS_GPG_KEY_ID" ]; then
    printf "ERROR: PASS_GPG_KEY_ID is not defined. Please provide a valid private GPG key ID.\\n" >&2
    exit 1
fi

if [ -z "$PASS_DIRECTORY" ]; then
    printf "WARNING: PASS_DIRECTORY is not defined.\\n" >&2
    exit 1
fi

# Add private SSH key to SSH agent for git pulls.
eval "$(ssh-agent -s)"
printf "%s\\n" "$PASS_SSH_PRIVATE_KEY" | ssh-add -

# Set up ~/.ssh/config to disable strict host key checking on github.com.
printf "Host github.com\\n    StrictHostKeyChecking no\\n\\nHost pass-operator-e2e\\n    StrictHostKeyChecking no\\n" > ~/.ssh/config
chmod 400 ~/.ssh/config

# Import public gpg key for secrets' encryption.
gpg --import <(echo "$PASS_GPG_KEY")

# # Initialize pass with the indicated directory and GPG key ID to decrypt secrets pulled from the Git repository.
# pass init --path="$PASS_DIRECTORY".git "$PASS_GPG_KEY_ID"

(
    git clone "${PASS_GIT_URL}" . \
    && cd "${PASS_DIRECTORY}" || exit 1 \
    && git checkout -b "${PASS_GIT_BRANCH}" \
    && git commit --allow-empty -m "Initial commit" \
    && git push -u origin "${PASS_GIT_BRANCH}"
)