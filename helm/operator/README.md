# Password Store Operator Installation

This operator requires the following items to start successfully.

- [private GPG key](#private-gpg-key) to decrypt the secrets that have been encrypted with a public key, locally
- [local pass store](#password-store) (on your local development machine)
- [git repository](#git-repository) populated by the local password store
- [private SSH key](#private-ssh-key) to clone the Git repository

I will go more in-depth and explain these requirements in the following sections.

## Private GPG key

The private GPG key is used by `pass` to decrypt your secrets that were encrypted on your local machine.

<details>
  <summary><b>Show</b></summary>

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

      > **Important:** if you specify a password for your key, you'll need to specify this password in the Helm values.

      You'll now see your key on your keyring.

      ```shell
      $ gpg --list-keys 51924ADAFC92656FAFEB672D4B90DE5D5BF143B8
      pub   rsa3072 2024-01-12 [SC] [expires: 2026-01-11]
            51924ADAFC92656FAFEB672D4B90DE5D5BF143B8
      uid           [ultimate] Emma Doyle <emma@premiscale.com>
      sub   rsa3072 2024-01-12 [E] [expires: 2026-01-11]
      ```

  2. Export your private key and b64 encode it (otherwise it will dump a bunch of binary data to your shell).

      ```shell
      $ gpg --armor --export-secret-keys 51924ADAFC92656FAFEB672D4B90DE5D5BF143B8 | base64
      ...
      ```

      Copy this value and update your [Helm values](/helm/operator/).

</details>

## Password store

Install [`pass`](https://www.passwordstore.org/) and initialize a local store using the GPG keys you generated in the last step.

<details>
    <summary><b>Show</b></summary>

```shell
pass init "$GPG_KEY_ID" --path <subpath of ~/.password-store/>
```

Now, on your local machine,

```shell
$ ls -lash ~/.password-store/repo/
total 12K
4.0K drwx------  2 emmadoyle emmadoyle 4.0K Jan 15 13:36 .
4.0K drwxrwxr-x 13 emmadoyle emmadoyle 4.0K Jan 15 13:36 ..
4.0K -rw-------  1 emmadoyle emmadoyle   41 Jan 15 13:36 .gpg-id
```
</details>

## Git repository

Link your local password store to a git repository.

<details>
    <summary><b>Show</b></summary>

From the `pass` [man page](https://git.zx2c4.com/password-store/about/),

```text
...
pass git git-command-args...
        If the password store is a git repository, execute a git command
        specified by git-command-args.
...
```

we may easily link our local password store to a remote Git repository. This operator uses `git` alongside `pass` to pull secret updates.

```shell
$ git init ~/.password-store/repo/
$ ls -lash ~/.password-store/repo/
total 16K
4.0K drwx------  3 emmadoyle emmadoyle 4.0K Jan 15 13:38 .
4.0K drwxrwxr-x 13 emmadoyle emmadoyle 4.0K Jan 15 13:36 ..
4.0K drwxrwxr-x  7 emmadoyle emmadoyle 4.0K Jan 15 13:38 .git
4.0K -rw-------  1 emmadoyle emmadoyle   41 Jan 15 13:36 .gpg-id
```

</details>

## Private SSH key

Now add a remote git repository and watch as `pass insert`-commands create local commits automatically. Sync your local password store with the remote repo via `pass git push`.

```text
helm upgrade --install helm/operator/
```

## Parameters

### Global Configuration

| Name                    | Description                                      | Value       |
| ----------------------- | ------------------------------------------------ | ----------- |
| `global.image.registry` | The global docker registry for all of the image. | `docker.io` |

### Operator Deployment

| Name                                         | Description                                                                                                                            | Value           |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| `deployment.pullSecrets`                     | A list of pull secret names. These names are automatically mapped to key: secretname in the imagePullSecrets field.                    | `[]`            |
| `deployment.image.name`                      | The name of the image.                                                                                                                 | `pass-operator` |
| `deployment.image.tag`                       | The tag of the image. The default is "ignore" to ensure users provide a tag.                                                           | `ignore`        |
| `deployment.image.pullPolicy`                | The pull policy of the image.                                                                                                          | `Always`        |
| `deployment.resources`                       | Set resources for the pod.                                                                                                             | `{}`            |
| `deployment.livenessProbe`                   | Configure the liveness probe for the pod. The defaults are set to check the /healthz endpoint on port 8080, which is provided by Kopf. | `{}`            |
| `deployment.podSecurityContext`              | Configure the security context for the pod.                                                                                            | `{}`            |
| `deployment.podSecurityContext.runAsNonRoot` | If true, the pod is required to run as a non-root user.                                                                                | `true`          |
| `deployment.containerSecurityContext`        | Configure the security context for the container.                                                                                      | `{}`            |

### Operator Configuration

| Name                         | Description                                                                                                                                                           | Value             |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| `operator.interval`          | The interval in seconds to check for changes in the secrets in the pass store.                                                                                        | `60`              |
| `operator.initial_delay`     | The initial delay in seconds before the first check for changes in the secrets in the pass store.                                                                     | `3`               |
| `operator.priority`          | The priority of the operator. The higher the number, the higher the priority. Only useful if multiple operators are running.                                          | `100`             |
| `operator.pass.binary`       | The path to the pass binary.                                                                                                                                          | `""`              |
| `operator.pass.storeSubPath` | A subpath within '~/.password-store'.                                                                                                                                 | `""`              |
| `operator.log.level`         | The log level for the operator. Options are: debug, info, warn, error.                                                                                                | `debug`           |
| `operator.ssh.createSecret`  | If true, the secret is created. Otherwise, the secret is only referenced. This allows for users to provide their own secret via SealedSecrets or some other operator. | `false`           |
| `operator.ssh.name`          | Name of the secret. If createSecret is false, this is used to reference an existing, user-provided secret.                                                            | `private-ssh-key` |
| `operator.ssh.value`         | The raw string of the secret key b64enc'd.                                                                                                                            | `""`              |
| `operator.gpg.createSecret`  | If true, the secret is created. Otherwise, the secret is only referenced. This allows for users to provide their own secret via SealedSecrets or some other operator. | `false`           |
| `operator.gpg.name`          | Name of the secret. If createSecret is false, this is used to reference an existing, user-provided secret.                                                            | `private-gpg-key` |
| `operator.gpg.key_id`        | The key ID of the (private) GPG key.                                                                                                                                  | `""`              |
| `operator.gpg.value`         | The raw string of the secret key b64enc'd.                                                                                                                            | `""`              |
| `operator.gpg.passphrase`    | The passphrase for the GPG key, if there is one.                                                                                                                      | `""`              |
| `operator.git.branch`        | The branch of the Git repository to clone and pull from.                                                                                                              | `main`            |
| `operator.git.url`           | The (SSH) URL of the Git repository. HTTPS is not supported at this time.                                                                                             | `""`              |

### Operator Service

| Name             | Description                                                                                                                                           | Value   |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `service.create` | If true, a service is created for the operator. This usually is not necessary as the operator is not listening on any ports except for a healthcheck. | `false` |

### Operator Service Account

| Name                    | Description                                                                         | Value           |
| ----------------------- | ----------------------------------------------------------------------------------- | --------------- |
| `serviceAccount.create` | If true, a service account is created for the operator. This is necessary for RBAC. | `true`          |
| `serviceAccount.name`   | The name of the service account.                                                    | `pass-operator` |

### Operator RBAC

| Name          | Description                                           | Value  |
| ------------- | ----------------------------------------------------- | ------ |
| `rbac`        | Configure the RBAC manifest for this Helm chart.      | `{}`   |
| `rbac.create` | If true, RBAC resources are created for the operator. | `true` |
