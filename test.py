#! /usr/bin/env python
# -*- coding: utf-8 -*-

from tests.e2e.lib import (
    # Tools
    check_cluster_pod_status,
    generate_gpg_keypair,
    generate_ssh_keypair,
    # Docker
    build_operator_image,
    cleanup_operator_image,
    build_e2e_image,
    cleanup_e2e_image,
    # Helm
    install_pass_operator_crds,
    uninstall_pass_operator_crds,
    install_pass_operator,
    uninstall_pass_operator,
    install_pass_operator_e2e,
    uninstall_pass_operator_e2e
)

import logging
import sys


log = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    level=logging.INFO
)


# Generate GPG and SSH keypairs for use in testing.
log.info('Generating GPG and SSH keypairs for testing.')
gpg_passphrase = '1234'
gpg_public_key, gpg_private_key, gpg_fingerprint = generate_gpg_keypair(
    passphrase=gpg_passphrase,
    delete_from_keyring=True
)
ssh_public_key, ssh_private_key = generate_ssh_keypair()
print(gpg_public_key, gpg_private_key, gpg_fingerprint, ssh_public_key, ssh_private_key)

log.info('Building e2e image')
# e2e artifacts that the operator depends on to run.
print(build_e2e_image(
    ssh_public_key=ssh_public_key,
    gpg_key_id=gpg_fingerprint,
    gpg_key=gpg_public_key,
    gpg_passphrase=gpg_passphrase
))

log.info('Installing pass-operator-e2e')
print(install_pass_operator_e2e(
    namespace='pass-operator-e2e'
))

log.info('Installing pass-operator crds')

# Build and install operator artifacts.
print(install_pass_operator_crds())

log.info('Building operator image')
print(build_operator_image())

log.info('Installing pass-operator')
print(install_pass_operator(
    ssh_value=ssh_private_key,
    gpg_value=gpg_private_key,
    gpg_key_id=gpg_fingerprint,
    namespace='pass-operator',
    ssh_createSecret=True,
    pass_storeSubPath='repo',
    gpg_createSecret=True,
    gpg_passphrase='',
    git_url='git+ssh://localhost:2222/pass-operator.git',
    git_branch='main'
))