#! /usr/bin/env bash
# Start the operator e2e container after some initial SSH, GPG, password store and git setup.


set -o pipefail


if [ -z "$SSH_PUBLIC_KEY" ]; then
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

mkdir ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
touch ~/.ssh/config
chmod 400 ~/.ssh/config

printf "%s" "$SSH_PUBLIC_KEY" > ~/.ssh/authorized_keys

# Import public gpg key for secrets' encryption.
gpg --import <(echo "$PASS_GPG_KEY")

# # Initialize pass with the indicated directory and GPG key ID to decrypt secrets pulled from the Git repository.
# pass init --path="$PASS_DIRECTORY".git "$PASS_GPG_KEY_ID"

(
    mkdir -p "$PASS_DIRECTORY".git || exit 1 \
    && chmod 777 "$PASS_DIRECTORY".git \
    && cd "$PASS_DIRECTORY".git \
    && git init \
    && git checkout -b "${PASS_GIT_BRANCH}" \
    && git commit --allow-empty -m "Initial commit"
)

# /usr/bin/git daemon --reuseaddr \
#     --export-all \
#     --max-connections=32 \
#     --port=22 \
#     --listen=0.0.0.0 \
#     --pid-file=/opt/operator/git.pid \
#     --base-path=/opt/operator/.password-store/ \
#     /opt/operator/.password-store/"$PASS_DIRECTORY" "$@"

mkdir /var/run/sshd

/usr/sbin/sshd -D -e \
    -o ListenAddress=0.0.0.0 \
    -o Port=22 \
    -o PasswordAuthentication=no \
    -o AuthorizedKeysFile=.ssh/authorized_keys \
    -o PidFile=/opt/operator/sshd.pid \
    -o ChallengeResponseAuthentication=no