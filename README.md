# Pasword Store Operator

This Kubernetes operator is proposed as a proof-of-concept. It can be used to sync and decrypt secrets from a password store ([pass](https://www.passwordstore.org/)) Git repository.

While this approach to secrets management on Kubernetes is more technically challenging, the advantage is that we don't have to rely on a 3rd party SaaS platform like Vault, Doppler,
or Infisical, et al. to hold our secrets. The benefits these platforms do provide, however, is better user and access management.

That said, I acknowledge that this approach swims against the DevSecOps tide in that it requires you to store your secrets (albeit encrypted) in Git, a practice
that's often discouraged and typically forbidden at most organizations.

## How it works

From a high level, this operator continually runs `git pull` on a specified interval to grab updates from a git repository populated with encrypted
secrets by `pass`. It maps secrets' paths to key values through the application of a [`PassSecret`](helm/operator/crds/PassSecret.yaml) Kubernetes [CRD](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/),
such as the following.

```yaml
apiVersion: secrets.premiscale.com/v1alpha1
kind: PassSecret
metadata:
  name: mysecret
  namespace: password-store-operator-tests
spec:
  data:
    - key: mykey
      path: premiscale/mydata
  managedSecret:
    name: mysecret
    namespace: premiscale
    type: Opaque
```

This operator requires the following items to start successfully.

- a private GPG key to decrypt the encrypted `pass` secrets
- a local password store
- a git repository populated by the local password store
- a private SSH key to clone the Git repository

I will go more in-depth and explain these requirements in the following sections.

### Private GPG key

#### Generating GPG keys

Run the following command to generate a GPG key.

```shell
gpg --generate-key
```

#### Converting GPG keys from binary to asc

```shell
gpg --enarmor /path/to/key.gpg
```

### Password store

### `pass` git repository

From the `pass` help text,

```text
...
pass git git-command-args...
        If the password store is a git repository, execute a git command
        specified by git-command-args.
...
```

we may easily link our local password store to a remote Git repository. This operator uses `git` alongside `pass` to pull secret updates (it never pushes them, however).