# Pass Store Operator Installation

```text
helm upgrade --install helm/operator/
```

## Parameters

### Global Configuration

| Name                    | Description                                                                           | Value       |
| ----------------------- | ------------------------------------------------------------------------------------- | ----------- |
| `global`                | Configure global settings for this Helm chart.                                        | `{}`        |
| `global.image`          | configure global docker settings used for all docker images referenced in this chart. | `{}`        |
| `global.image.registry` | The global docker registry for all of the image.                                      | `docker.io` |

### Operator Deployment

| Name                                         | Description                                                                                                                            | Value           |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| `deployment`                                 | Configure the deployment manifest for this Helm chart.                                                                                 | `{}`            |
| `deployment.pullSecrets`                     | A list of pull secret names. These names are automatically mapped to key: secretname in the imagePullSecrets field.                    | `[]`            |
| `deployment.image`                           | Configure the image used for the deployment.                                                                                           | `{}`            |
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
| `operator`                   | Configure operator-specific settings.                                                                                                                                 | `{}`              |
| `operator.interval`          | The interval in seconds to check for changes in the secrets in the pass store.                                                                                        | `60`              |
| `operator.initial_delay`     | The initial delay in seconds before the first check for changes in the secrets in the pass store.                                                                     | `3`               |
| `operator.priority`          | The priority of the operator. The higher the number, the higher the priority. Only useful if multiple operators are running.                                          | `100`             |
| `operator.pass`              | Configure the pass store.                                                                                                                                             | `{}`              |
| `operator.pass.binary`       | The path to the pass binary.                                                                                                                                          | `""`              |
| `operator.pass.storeSubPath` | A subpath within '~/.password-store'.                                                                                                                                 | `""`              |
| `operator.log`               | Configure the log level for the operator.                                                                                                                             | `{}`              |
| `operator.log.level`         | The log level for the operator. Options are: debug, info, warn, error.                                                                                                | `debug`           |
| `ssh`                        | Configure the SSH secret.                                                                                                                                             | `{}`              |
| `operator.ssh.createSecret`  | If true, the secret is created. Otherwise, the secret is only referenced. This allows for users to provide their own secret via SealedSecrets or some other operator. | `false`           |
| `operator.ssh.name`          | Name of the secret. If createSecret is false, this is used to reference an existing, user-provided secret.                                                            | `private-ssh-key` |
| `operator.ssh.value`         | The raw string of the secret key b64enc'd.                                                                                                                            | `""`              |
| `operator.gpg`               | Configure the GPG (private key) secret.                                                                                                                               | `{}`              |
| `operator.gpg.createSecret`  | If true, the secret is created. Otherwise, the secret is only referenced. This allows for users to provide their own secret via SealedSecrets or some other operator. | `false`           |
| `operator.gpg.name`          | Name of the secret. If createSecret is false, this is used to reference an existing, user-provided secret.                                                            | `private-gpg-key` |
| `operator.gpg.key_id`        | The key ID of the (private) GPG key.                                                                                                                                  | `""`              |
| `operator.gpg.value`         | The raw string of the secret key b64enc'd.                                                                                                                            | `""`              |
| `operator.gpg.passphrase`    | The passphrase for the GPG key, if there is one.                                                                                                                      | `""`              |
| `operator.git`               | Configure the Git repository for the pass store.                                                                                                                      | `{}`              |
| `operator.git.branch`        | The branch of the Git repository to clone and pull from.                                                                                                              | `main`            |
| `operator.git.url`           | The (SSH) URL of the Git repository. HTTPS is not supported at this time.                                                                                             | `""`              |

### Operator Service

| Name             | Description                                                                                                                                           | Value   |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `service`        | Configure the service manifest for this Helm chart.                                                                                                   | `{}`    |
| `service.create` | If true, a service is created for the operator. This usually is not necessary as the operator is not listening on any ports except for a healthcheck. | `false` |

### Operator Service Account

| Name                    | Description                                                                         | Value           |
| ----------------------- | ----------------------------------------------------------------------------------- | --------------- |
| `serviceAccount`        | Configure the service account manifest for this Helm chart.                         | `{}`            |
| `serviceAccount.create` | If true, a service account is created for the operator. This is necessary for RBAC. | `true`          |
| `serviceAccount.name`   | The name of the service account.                                                    | `pass-operator` |

### Operator RBAC

| Name          | Description                                           | Value  |
| ------------- | ----------------------------------------------------- | ------ |
| `rbac`        | Configure the RBAC manifest for this Helm chart.      | `{}`   |
| `rbac.create` | If true, RBAC resources are created for the operator. | `true` |
