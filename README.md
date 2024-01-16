# `pass` secrets operator

This Kubernetes operator can be used to sync and decrypt secrets from a password store ([pass](https://www.passwordstore.org/)) Git repository. It is proposed as a proof-of-concept and shouldn't be used in any production capacity.

While this approach to secrets management on Kubernetes is more technically challenging, the advantage is that we don't have to rely on a 3rd party SaaS platform, such as Vault or Doppler, to hold our secrets (the obvious benefits these platforms do provide, however, are better user and access management). We may also use this operator in an airgapped environment with a self-hosted git repository.

<!--
I also acknowledge that this approach swims against the DevSecOps tide in that it requires you to store your secrets (albeit encrypted)
in Git, a practice that is often discouraged and typically forbidden at most organizations.
-->

## How it works

From a high level, this operator runs `git pull` on an interval to grab updates from a git repository populated with encrypted
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
    namespace: pass-operator-test
    type: Opaque
    immutable: false
```

The above `PassSecret` manifest translates to the following `Secret`.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mysecret
  namespace: pass-operator-test
data:
  mykey: <contents of premiscale/mydata>
immutable: false
type: Opaque
```

## Use

This operator requires the following items to start successfully.

- private GPG key to decrypt the secrets that have been encrypted with a public key, locally
- local pass store (on your local development machine)
- git repository populated by the local password store
- private SSH key to clone the Git repository

I will go more in-depth and explain these requirements in the following sections.

### Private GPG key

The private GPG key is used by `pass` to decrypt your secrets that were encrypted on your local machine. See the [GPG documentation](docs/setup/gpg.md) for a more in-depth suite of commands to get set up with RSA keys for use with this operator.

### Password store

Install [`pass`](https://www.passwordstore.org/) and initialize a local store using the GPG keys you generated in the last step.

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

### Git repository

From the `pass` help text,

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

### Private SSH key

Now add a remote git repository and watch as `pass insert`-commands create local commits automatically. Sync your local password store with the remote repo via `pass git push`.
