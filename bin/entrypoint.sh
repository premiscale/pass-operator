#! /usr/bin/env bash
# Start the pass operator after some initial SSH setup.

eval "$(ssh-agent -s)"
printf "%s" "$SSH_PRIVATE_KEY" > ~/.ssh/private-key
ssh-add ~/.ssh/private-key