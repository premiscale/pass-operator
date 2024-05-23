# `operator-e2e` Helm Chart

This chart is intended to deploy and orchestrate an e2e test Git repository that's populated with randomly-generated secrets in a pass store.

Note that this project in particular uses only public keys, and so its secrets' names do not conflict with those of the [`operator`](../operator/) chart, if they're created.

## Install

This Helm chart isn't intended to be installed directly. See the logic in [src/test/e2e/lib.py](../../src/test/e2e/lib.py) that provides a Python
interface to installing this chart and others in a local e2e testing environment.

## Parameters

### Global Configuration

| Name                    | Description                                      | Value       |
| ----------------------- | ------------------------------------------------ | ----------- |
| `global.image.registry` | The global docker registry for all of the image. | `docker.io` |

### E2E Deployment

| Name                                  | Description                                                                                                         | Value           |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | --------------- |
| `deployment.pullSecrets`              | A list of pull secret names. These names are automatically mapped to key: secretname in the imagePullSecrets field. | `[]`            |
| `deployment.image.name`               | The name of the image.## @param deployment.image.name [string, default: pass-operator] The name of the image.       | `pass-operator` |
| `deployment.image.tag`                | The tag of the image. The default is "ignore" to ensure users provide a tag.                                        | `ignore`        |
| `deployment.image.pullPolicy`         | The pull policy of the image.                                                                                       | `Always`        |
| `deployment.resources`                | Set resources for the pod.                                                                                          | `{}`            |
| `deployment.livenessProbe`            | Configure the liveness probe for the pod. The defaults are set to check that SSHd is listening on TCP port 22.      | `{}`            |
| `deployment.podSecurityContext`       | Configure the security context for the pod.                                                                         | `{}`            |
| `deployment.containerSecurityContext` | Configure the security context for the container.                                                                   | `{}`            |

### Operator Configuration

| Name                         | Description                                                                                                                                                           | Value            |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| `operator.pass.binary`       | The path to the pass binary.                                                                                                                                          | `""`             |
| `operator.pass.storeSubPath` | A subpath within '~/.password-store'.                                                                                                                                 | `""`             |
| `operator.ssh.createSecret`  | If true, the secret is created. Otherwise, the secret is only referenced. This allows for users to provide their own secret via SealedSecrets or some other operator. | `false`          |
| `operator.ssh.name`          | Name of the secret. If createSecret is false, this is used to reference an existing, user-provided secret.                                                            | `public-ssh-key` |
| `operator.ssh.value`         | The raw string of the public SSH key b64enc'd.                                                                                                                        | `""`             |
| `operator.gpg.createSecret`  | If true, the secret is created. Otherwise, the secret is only referenced. This allows for users to provide their own secret via SealedSecrets or some other operator. | `false`          |
| `operator.gpg.name`          | Name of the secret. If createSecret is false, this is used to reference an existing, user-provided secret.                                                            | `public-gpg-key` |
| `operator.gpg.key_id`        | The key ID of the (public) GPG key.                                                                                                                                   | `""`             |
| `operator.gpg.value`         | The armored string of the public GPG key b64enc'd.                                                                                                                    | `""`             |
| `operator.gpg.passphrase`    | The passphrase for the GPG key, if there is one.                                                                                                                      | `""`             |
| `operator.git.branch`        | The branch of the Git repository to clone and pull from.                                                                                                              | `main`           |

### E2E Service

| Name             | Description                                                                                                                | Value       |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------- |
| `service.create` | If true, a service is created for the operator e2e pod. This makes cloning the repo easier.                                | `true`      |
| `service.type`   | The type of service to create. This is usually ClusterIP as there's no need for external access.                           | `ClusterIP` |
| `service.ports`  | The ports to expose on the service. Default is to expose port 22 as SSHd is listening on this port for connections by git. | `{}`        |
