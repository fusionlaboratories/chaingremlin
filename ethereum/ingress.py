
from kubernetes import client, config

def create_ingress_resource(ethereum_node):
    config.load_kube_config()  # Load Kubernetes configuration from the default location

    networking_v1 = client.NetworkingV1Api()  # Use the V1 API instead of V1Beta1

    ingress = client.V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=client.V1ObjectMeta(
            name=f"eth-node-{ethereum_node.node_id}-ingress",
        ),
        spec=client.V1IngressSpec(
            rules=[
                client.V1IngressRule(
                    http=client.V1HTTPIngressRuleValue(
                        paths=[
                            client.V1HTTPIngressPath(
                                path=f"/eth/{ethereum_node.namespace}/node_{ethereum_node.node_id}/http_rpc/",
                                path_type="Exact",
                                backend=client.V1IngressBackend(
                                    service=client.V1IngressServiceBackend(
                                        port=client.V1ServiceBackendPort(
                                            number=8545
                                        ),
                                        name=f"exec-{ethereum_node.node_id}",
                                    ),
                                ),
                            ),
                            client.V1HTTPIngressPath(
                                path=f"/eth/{ethereum_node.namespace}/node_{ethereum_node.node_id}/auth_rpc/",
                                path_type="Exact",
                                backend=client.V1IngressBackend(
                                    service=client.V1IngressServiceBackend(
                                        port=client.V1ServiceBackendPort(
                                            number=8551
                                        ),
                                        name=f"exec-{ethereum_node.node_id}",
                                    ),
                                ),
                            ),
                            client.V1HTTPIngressPath(
                                path=f"/eth/{ethereum_node.namespace}/node_{ethereum_node.node_id}/beacon_api/",
                                path_type="Exact",
                                backend=client.V1IngressBackend(
                                    service=client.V1IngressServiceBackend(
                                        port=client.V1ServiceBackendPort(
                                            number=5052
                                        ),
                                        name=f"beacon-{ethereum_node.node_id}",
                                    ),
                                ),
                            ),
                            client.V1HTTPIngressPath(
                                path=f"/eth/{ethereum_node.namespace}/node_{ethereum_node.node_id}/beacon_p2p/",
                                path_type="Exact",
                                backend=client.V1IngressBackend(
                                    service=client.V1IngressServiceBackend(
                                        port=client.V1ServiceBackendPort(
                                            number=30303
                                        ),
                                        name=f"beacon-{ethereum_node.node_id}",
                                    ),
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )

    # Create the Ingress resource
    networking_v1.create_namespaced_ingress(ethereum_node.namespace, ingress)
    ingress_host = 'localhost:8081'
    ethereum_node.execution_client_endpoints.http_rpc_ingress_endpoint = f"http://{ingress_host}/eth/{ethereum_node.namespace}/node_{ethereum_node.node_id}/http_rpc/"
    ethereum_node.execution_client_endpoints.auth_rpc_ingress_endpoint = f"http://{ingress_host}/eth/{ethereum_node.namespace}/node_{ethereum_node.node_id}/auth_rpc/"
    ethereum_node.consensus_client_endpoints.HTTP_API_ingress_endpoint = f"http://{ingress_host}/eth/{ethereum_node.namespace}/node_{ethereum_node.node_id}/beacon_api/"
    ethereum_node.consensus_client_endpoints.P2P_ingress_endpoint = f"http://{ingress_host}/eth/{ethereum_node.namespace}/node_{ethereum_node.node_id}/beacon_p2p/"
    return ethereum_node