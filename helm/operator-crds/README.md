# `operator-crds` Custom Resources Helm Chart

This Helm chart is very simple, it only contains the `PassSecret` CRDs that the operator uses to create managed `Secret`s at users' request.

## Parameters

### Global Configuration

| Name              | Description                                          | Value |
| ----------------- | ---------------------------------------------------- | ----- |
| `global.versions` | list of supported versions that are to be installed. | `[]`  |
