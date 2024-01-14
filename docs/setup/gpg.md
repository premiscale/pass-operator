# Generating GPG keys

You can find a lot of explanation about how to generate keys with GPG online, but I'll write down my process below for generating keys to use with this operator.

1. First, generate a key.

    ```shell
    $ gpg --generate-key
    gpg (GnuPG) 2.2.27; Copyright (C) 2021 Free Software Foundation, Inc.
    This is free software: you are free to change and redistribute it.
    There is NO WARRANTY, to the extent permitted by law.

    Note: Use "gpg --full-generate-key" for a full featured key generation dialog.

    GnuPG needs to construct a user ID to identify your key.

    Real name: Emma Doyle
    Email address: emma@premiscale.com
    You selected this USER-ID:
    "Emma Doyle <emma@premiscale.com>"

    Change (N)ame, (E)mail, or (O)kay/(Q)uit? O
    We need to generate a lot of random bytes. It is a good idea to perform
    some other action (type on the keyboard, move the mouse, utilize the
    disks) during the prime generation; this gives the random number
    generator a better chance to gain enough entropy.
    We need to generate a lot of random bytes. It is a good idea to perform
    some other action (type on the keyboard, move the mouse, utilize the
    disks) during the prime generation; this gives the random number
    generator a better chance to gain enough entropy.
    gpg: key 4B90DE5D5BF143B8 marked as ultimately trusted
    gpg: revocation certificate stored as '/home/emmadoyle/.gnupg/openpgp-revocs.d/51924ADAFC92656FAFEB672D4B90DE5D5BF143B8.rev'
    public and secret key created and signed.

    pub   rsa3072 2024-01-12 [SC] [expires: 2026-01-11]
          51924ADAFC92656FAFEB672D4B90DE5D5BF143B8
    uid                      Emma Doyle <emma@premiscale.com>
    sub   rsa3072 2024-01-12 [E] [expires: 2026-01-11]

    ```

    > **Important:** be sure not to specify a password to use your keys.

    You'll now see your key on your keyring.

    ```shell
    gpg --list-keys 51924ADAFC92656FAFEB672D4B90DE5D5BF143B8
    pub   rsa3072 2024-01-12 [SC] [expires: 2026-01-11]
          51924ADAFC92656FAFEB672D4B90DE5D5BF143B8
    uid           [ultimate] Emma Doyle <emma@premiscale.com>
    sub   rsa3072 2024-01-12 [E] [expires: 2026-01-11]
    ```

2. Export your private key and b64 encode it (otherwise it will dump a bunch of binary data to your shell).

    ```shell
    gpg --armor --export-secret-keys D1847B5ACFFB05196518D403DF04830B1AE47FD2 | base64
    ...
    ```

    Copy this value and update your [Helm values](/helm/operator/).