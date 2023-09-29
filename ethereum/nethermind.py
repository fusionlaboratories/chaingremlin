from kubernetes import client, config
from  ethereum.models import execution_client_endpoints

def init_nethermind(namespace, node_id, genesis_uri, bootnode_svc_endpoint=None, image_pull_secret=None):
    config.load_kube_config()

    api_instance = client.CoreV1Api()
    
    bootnode_setup_cmd = ''
    bootnode_discovery_flag = ''
    if bootnode_svc_endpoint:
        bootnode_endpoint = bootnode_svc_endpoint.replace('http://', '')
        bootnode_setup_cmd = f'''
        while ! wget -T 5 -c {bootnode_endpoint}/; do sleep 10; done;
        wget --header="Content-Type: application/json" --post-data='{{"method":"net_localEnode","params":[],"id":1,"jsonrpc":"2.0"}}' -O- {bootnode_endpoint}/ |jq -r '.result' > /data/bootnodes.txt
        '''
        bootnode_discovery_flag = f'''--Discovery.Bootnodes=$(cat /data/bootnodes.txt)'''
        
    init_genesis_command = [
        'sh',
        '-ace',
        f'''while ! wget -T 5 -c {genesis_uri}/; do sleep 5; done; GENESIS_URI={genesis_uri}/custom_config_data/chainspec.json;
        TRUSTED_SETUP_URI={genesis_uri}/custom_config_data/trusted_setup.txt;
        if ! [ -f /data/genesis_init_done ]; then
        wget -O /data/genesis.json $GENESIS_URI;
        wget -O /data/trusted_setup.txt $TRUSTED_SETUP_URI;
        apk update && apk add jq;
        cat /data/genesis.json | jq -r '.config.chainId' > /data/chainid.txt;
        {bootnode_setup_cmd}
        touch /data/genesis_init_done;
        echo "genesis init done";
        else
        echo "genesis is already initialized";
        fi;'''
    ]

    pod_manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'labels': {
                'app.kubernetes.io/instance': f'exec-{node_id}',
                'app.kubernetes.io/name': 'execution',
                'ethereum_role': 'execution',
                'execution_client': 'nethermind',
                'node_id': str(node_id)
            },
            'name': f'exec-{node_id}'
        },
        'spec': {
            'containers': [{
                'command': [
                    'sh',
                    '-ace',
                    f'''exec /nethermind/Nethermind.Runner --datadir=/data --KeyStore.KeyStoreDirectory=/data/keystore --Network.LocalIp=$(POD_IP) --Network.ExternalIp=$(POD_IP) --Network.P2PPort=30303 --Network.DiscoveryPort=30303 --JsonRpc.Enabled=true --JsonRpc.Host=0.0.0.0 --JsonRpc.Port=8545 --JsonRpc.JwtSecretFile=/data/jwt.hex --JsonRpc.EngineHost=0.0.0.0 --JsonRpc.EnginePort=8551 --Metrics.Enabled=true --Metrics.NodeName=$(POD_NAME) --Metrics.ExposePort=9545 --Init.ChainSpecPath=/data/genesis.json --config=none.cfg --Init.IsMining=false --Pruning.Mode=None --JsonRpc.EnabledModules=Eth,Subscribe,Trace,TxPool,Web3,Personal,Proof,Net,Parity,Health,Rpc,Debug,Admin --EthStats.Enabled=false --log=DEBUG --Merge.Enabled=true {bootnode_discovery_flag}'''
                ],
                'image': 'nethermind/nethermind:latest',
                'name': 'nethermind-container',
                'ports': [{'containerPort': 30303}, {'containerPort': 8545}, {'containerPort': 8551}],
                'volumeMounts': [
                    {'mountPath': '/data', 'name': 'storage'},
                    {'mountPath': '/data/jwt.hex', 'name': 'jwt', 'subPath': 'jwt.hex', 'readOnly': True}
                ],
                'env': [
                    {
                        'name': 'POD_IP',
                        'valueFrom': {'fieldRef': {'fieldPath': 'status.podIP'}}
                    },
                    {
                        'name': 'POD_NAME',
                        'valueFrom': {'fieldRef': {'fieldPath': 'metadata.name'}}
                    }
                ],
                'readinessProbe': {
                    'failureThreshold': 3,
                    'initialDelaySeconds': 30,
                    'periodSeconds': 10,
                    'successThreshold': 1,
                    'tcpSocket': {'port': 8545}
                },
                'livenessProbe': {
                    'failureThreshold': 3,
                    'initialDelaySeconds': 30,
                    'periodSeconds': 10,
                    'successThreshold': 1,
                    'tcpSocket': {'port': 8545}
                },
                'resources': {
                    'limits': {
                        'cpu': '3',
                        'memory': '7Gi'
                    }
                },
                'workingDir': '/data'
            }],
            'initContainers': [
                {
                    'command': init_genesis_command,
                    'image': 'alpine:latest',
                    'imagePullPolicy': 'IfNotPresent',
                    'name': 'init-genesis',
                    'volumeMounts': [{'mountPath': '/data', 'name': 'storage'}],
                    'resources': {},
                    'securityContext': {'runAsUser': 0, 'runAsNonRoot': False}
                },
                {
                    'image': 'busybox',
                    'imagePullPolicy': 'IfNotPresent',
                    'name': 'init-chown-data',
                    'resources': {},
                    'command': ['chown', '-R', '10001:10001', '/data'],
                    'volumeMounts': [{'mountPath': '/data', 'name': 'storage'}],
                    'securityContext': {'runAsUser': 0, 'runAsNonRoot': False}
                }
            ],
            'imagePullSecrets': [{'name': image_pull_secret}] if image_pull_secret else [],
            'volumes': [
                {'name': 'storage', 'emptyDir': {}},
                {'name': 'jwt', 'secret': {'secretName': 'jwt'}}
            ]
        }
    }
    
    api_instance.create_namespaced_pod(namespace=namespace, body=pod_manifest)

    # Prepare the Service manifest
    service_manifest = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'labels': {
                'app.kubernetes.io/instance': f'exec-{node_id}',
              'app.kubernetes.io/name': 'execution',
              'ethereum_role': 'execution',
              'execution_client': 'nethermind',
              'node_id': str(node_id)
            },
            'name': f'exec-{node_id}'
        },
        'spec': { 
            'ports': [{
                'name': 'p2p',
                'port': 30303,
                'protocol': 'TCP',
                'targetPort': 30303
            }, {
                'name': 'rpc',
                'port': 8545,
                'protocol': 'TCP',
                'targetPort': 8545
            },
            {
                'name': 'auth-rpc',
                'port': 8551,
                'protocol': 'TCP',
                'targetPort': 8551
            }
             , {
                'name': 'metrics',
                'port': 9545,
                'protocol': 'TCP',
                'targetPort': 9545
            }],
            'selector': {
              'app.kubernetes.io/instance': f'exec-{node_id}',
              'app.kubernetes.io/name': 'execution',
              'ethereum_role': 'execution',
              'execution_client': 'nethermind',
              'node_id': str(node_id)
            },
            'type': 'ClusterIP'
        }
    }

    # Create the Service
    api_response = api_instance.create_namespaced_service(namespace=namespace, body=service_manifest)
    return execution_client_endpoints(
        http_rpc_svc_endpoint=f'http://exec-{node_id}.{namespace}.svc.cluster.local:8545',
        http_rpc_ingress_endpoint= f'http://exec-{node_id}.{namespace}.svc.cluster.local:8545',
        auth_rpc_svc_endpoint= f'http://exec-{node_id}.{namespace}.svc.cluster.local:8551',
        auth_rpc_ingress_endpoint= f'http://exec-{node_id}.{namespace}.svc.cluster.local:8551'
    )

