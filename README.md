# Pasword Store Operator

This Kubernetes operator can be used to sync and decrypt secrets from a [pass](https://www.passwordstore.org/) Git repository.

## Usage

### Pip

#### Install

```shell
pip install password-store-operator
```

#### Upgrade

```shell
pip install --upgrade pass-operator
```

### Helm

See the [README](helm/operator/README.md) for more in-depth installation instructions.

#### Registry

```shell
helm repo add password-store-operator
```

#### Install

```shell
helm install password-store-operator
```

#### Upgrade

```shell
helm upgrade --install
```