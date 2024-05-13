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

# Uninstalling prior Helm chart installations.
uninstall_pass_operator(namespace='pass-operator')
uninstall_pass_operator_e2e(namespace='pass-operator')
uninstall_pass_operator_crds(namespace='pass-operator')


# Generate GPG and SSH keypairs for use in testing.
log.info('Generating GPG and SSH keypairs for testing.')
gpg_passphrase = '1234'
gpg_public_key, gpg_private_key, gpg_fingerprint = generate_gpg_keypair(
    passphrase=gpg_passphrase,
    delete_from_keyring=True
)
ssh_public_key, ssh_private_key = generate_ssh_keypair()

log.info('Building e2e image')
# e2e artifacts that the operator depends on to run.
build_e2e_image()

log.info('Installing pass-operator-e2e')
install_pass_operator_e2e(
    ssh_value=ssh_public_key,
    gpg_value=gpg_public_key,
    gpg_key_id=gpg_fingerprint,
    namespace='pass-operator',
    ssh_createSecret=True,
    pass_storeSubPath='repo',
    gpg_createSecret=True,
    gpg_passphrase='1234',
    git_branch='main'
)

log.info('Installing pass-operator crds')

# Build and install operator artifacts.
install_pass_operator_crds(namespace='pass-operator')

log.info('Building operator image')
build_operator_image()

log.info('Installing pass-operator')
install_pass_operator(
    ssh_value=ssh_private_key,
    gpg_value=gpg_private_key,
    gpg_key_id=gpg_fingerprint,
    namespace='pass-operator',
    ssh_createSecret=True,
    pass_storeSubPath='repo',
    gpg_createSecret=True,
    gpg_passphrase='1234',
    git_url='git+ssh://pass-operator-e2e/pass-operator/repo.git',
    git_branch='main'
)


cleanup_e2e_image()
cleanup_operator_image()