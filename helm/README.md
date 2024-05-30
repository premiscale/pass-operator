# Operator and supporting Helm charts

- [`operator`](https://github.com/premiscale/pass-operator/tree/master/helm/operator) is the chart for deploying the pass store operator
- [`operator-crds`](https://github.com/premiscale/pass-operator/tree/master/helm/operator-crds) is the chart for deploying the pass store operator's custom resource definitions (CRDs)
- [`operator-e2e`](https://github.com/premiscale/pass-operator/tree/master/helm/operator-e2e) is a chart for e2e-testing the operator and its CRDs. Unless you're a developer, you won't need to use this Helm chart.