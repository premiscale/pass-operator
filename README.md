# `pass` secrets operator

This Kubernetes operator can be used to sync and decrypt secrets from a password store ([pass](https://www.passwordstore.org/)) Git repository. It is proposed as a proof-of-concept and shouldn't be used in any production capacity.

While this approach to secrets management on Kubernetes is more technically challenging, the advantage is that we don't have to rely on a 3rd party SaaS platform like Vault, Doppler, or Infisical, et al. to hold our secrets. (The benefits these platforms do provide, however, is better user and access management.)

I also acknowledge that this approach swims against the DevSecOps tide in that it requires you to store your secrets (albeit encrypted)
in Git, a practice that is often discouraged and typically forbidden at most organizations.

## How it works

From a high level, this operator continually runs `git pull` on a specified interval to grab updates from a git repository populated with encrypted
secrets by `pass`. It maps secrets' paths to key values through the application of a [`PassSecret`](helm/operator/crds/PassSecret.yaml) Kubernetes [CRD](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/),
such as the following.

```yaml
apiVersion: secrets.premiscale.com/v1alpha1
kind: PassSecret
metadata:
  name: mysecret
  namespace: pass-operator-test
spec:
  data:
    - key: mykey
      path: premiscale/mydata
  managedSecret:
    name: mysecret
    namespace: premiscale
    type: Opaque
```

## Use

This operator requires the following items to start successfully.

- a private GPG key to decrypt the secrets that have been encrypted with a public GPG key
- a local pass store
- a git repository connected to and populated by the local password store
- a private SSH key to clone the Git repository

I will go more in-depth and explain these requirements in the following sections.

### Private GPG key

The private GPG key is used by `pass` to decrypt your secrets that were encrypted on your local machine. See the [GPG documentation](docs/setup/gpg.md) for a more in-depth suite of commands to get set up with RSA keys.

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