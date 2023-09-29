# Chaingremlin 

Chaingremlin is a platform for orchestrating blockchains, execute events like account creations and transfers and inject adversarial conditions in the network. Given a chain specification, a topology is created in Kubernetes, and events are then executed. Chaingremlin also allows for fault injection (currently latency and network partitioning) to simulate adversarial conditions in the chain.


## getting started
> k3d cluster create l1 -p "8081:80@loadbalancer" --agents 4 
> python main.py

# TODO: 
- [] hardcoded cluster domain and ingresshost (currently localhost:8081)
- [] For simplicity, all nodes currently share the same jwt-secret. Should be randomly generated per node
- [] parametereize resource quotas. Requests/limits are set too high thus requiring a lot of resources
- [] parameterize kubeconfig credentials. Currently reads .kube/config and instantiate a client in each function
- [] BTC signet
- [] Lodestar validator mnemonic is hardcoded and not read from secret

