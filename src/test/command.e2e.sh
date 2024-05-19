#! /usr/bin/env bash
# Start the operator e2e container after some initial SSH, GPG, password store and git setup.


set -o pipefail
shopt -s nullglob


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

# I took this from https://stackoverflow.com/a/53886735
gpg --list-keys --fingerprint | grep pub -A 1 | grep -Ev "pub|--" | tr -d ' ' \
 | awk 'BEGIN { FS = "\n" } ; { print $1":6:" } ' | gpg --import-ownertrust

# Initialize pass with the indicated directory and GPG key ID to decrypt secrets pulled from the Git repository.
pass init --path="$PASS_DIRECTORY".git "$PASS_GPG_KEY_ID"

function populate_pass_store()
{
    local f path paths

    for f in "$HOME"/data/crd/*.unencrypted.yaml; do
        mapfile -t paths < <(yq '.spec.encryptedData | to_entries[].key' "$f")

        for path in "${paths[@]}"; do
            printf "Processing path \"%s\" from unencrypted secret \"%s\"\\n" "$path" "$f"
            printf "%s" "$(yq ".spec.encryptedData.\"$path\"" "$f" | awk NF)" | pass insert --echo "$PASS_DIRECTORY".git/"$path"
        done
    done
}

# Set up the git repo to be accessible at $host/root/"$PASS_DIRECTORY".git
(
    ln -s "$HOME"/.password-store/"$PASS_DIRECTORY".git "$HOME"/"$PASS_DIRECTORY".git \
    && cd "$HOME"/"$PASS_DIRECTORY".git || exit 1 \
    && git config --global init.defaultBranch "$PASS_GIT_BRANCH" \
    && git config --global user.email "emmatest@premiscale.com" \
    && git config --global user.name "Emma Doyle" \
    && git init --bare
)

# Populate the pass store with the secrets from the CRDs.
(
    git clone "$HOME"/"$PASS_DIRECTORY".git "$HOME"/"$PASS_DIRECTORY" \
    && populate_pass_store \
    && cp -R "$HOME"/.password-store/"$PASS_DIRECTORY".git/premiscale "$HOME"/"$PASS_DIRECTORY" \
    && cp "$HOME"/.password-store/"$PASS_DIRECTORY".git/.gpg-id "$HOME"/"$PASS_DIRECTORY" \
    && cd "$HOME"/"$PASS_DIRECTORY" || exit 1 \
    && printf "Initial pass repository for e2e tests." > README.md \
    && git add . \
    && git commit -m "Initial commit" \
    && git push origin "$PASS_GIT_BRANCH"
)

rm -rf "${HOME:?}"/"${PASS_DIRECTORY:?}"

mkdir /var/run/sshd

/usr/sbin/sshd -D -e \
    -o ListenAddress=0.0.0.0 \
    -o Port=22 \
    -o PasswordAuthentication=no \
    -o AuthorizedKeysFile=.ssh/authorized_keys \
    -o PidFile="$HOME"/sshd.pid \
    -o ChallengeResponseAuthentication=no