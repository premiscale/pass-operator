# Pass kubernetes operator

This Kubernetes operator can be used to sync and decrypt secrets from a [pass](https://www.passwordstore.org/) Git repository.

## Setup

### Installation

```shell
pip install pass-operator
```

### Upgrading

```shell
pip install --upgrade pass-operator
```

### Helm deployment

```shell
helm upgrade --install
```

## Plan

1. Get a 1c 1GiB version 1.0.0 out there.
2. Cut version 2.0.0 with multiprocessing / queuing in the event there's a lot of namespaces to handle.
3. cut version 3.0.0 with a frontend / ingress.