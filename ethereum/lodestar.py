from pprint import pprint
from kubernetes import client, config
from ethereum.models import consensus_client_endpoints 

def init_lodestar(namespace, node_id, genesis_uri, target_peers, execution_client_uri,beacon_bootnode_uri=None,image_pull_secret=None):
    config.load_kube_config()

    api_instance = client.CoreV1Api()
    bootnode_setup_cmd=''
    bootnode_enr_cmd=""
    if beacon_bootnode_uri:
        bootnode_setup_cmd = f'''while ! wget -T 5 -c {beacon_bootnode_uri}/eth/v1/node/identity; do sleep 10; done;
        wget -O- {beacon_bootnode_uri}/eth/v1/node/identity | jq -r '.data.enr' >> /data/testnet_spec/bootstrap_nodes.txt;
        cat /data/testnet_spec/bootstrap_nodes.txt

        '''
        bootnode_enr_cmd = f'--bootnodes=$(cat /data/testnet_spec/bootstrap_nodes.txt) --network.connectToDiscv5Bootnodes=true'
        
    init_genesis_command = [
        'sh',
        '-ace',
        f'''while ! wget -T 5 -c {genesis_uri}/; do sleep 5; done; DEPOSIT_CONTRACT_URI={genesis_uri}/custom_config_data/deposit_contract.txt; DEPOSIT_CONTRACT_BLOCK_URI={genesis_uri}/custom_config_data/deposit_contract_block.txt; DEPLOY_BLOCK_URI={genesis_uri}/custom_config_data/deploy_block.txt; GENESIS_CONFIG_URI={genesis_uri}/custom_config_data/config.yaml; GENESIS_SSZ_URI={genesis_uri}/custom_config_data/genesis.ssz; TRUSTED_SETUP_URI={genesis_uri}/custom_config_data/trusted_setup.txt; mkdir -p /data/testnet_spec; apk update && apk add jq;
      if ! [ -f /data/testnet_spec/genesis.ssz ]; then
        wget -O /data/testnet_spec/deposit_contract.txt $DEPOSIT_CONTRACT_URI;
        wget -O /data/testnet_spec/deposit_contract_block.txt $DEPOSIT_CONTRACT_BLOCK_URI;
        wget -O /data/testnet_spec/deploy_block.txt $DEPLOY_BLOCK_URI;
        wget -O /data/testnet_spec/config.yaml $GENESIS_CONFIG_URI;
        wget -O /data/testnet_spec/genesis.ssz $GENESIS_SSZ_URI;

        {bootnode_setup_cmd}
        echo "genesis init done";

      else
        echo "genesis exists. skipping...";
      fi;
        '''
    ]

    pod_manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'labels': {
                'app.kubernetes.io/instance': f'beacon-{node_id}',
                'app.kubernetes.io/name': 'beacon',
                'consensus_client': 'lodestar',
                'ethereum_role': 'consensus',
                'node_id': str(node_id)
            },
            'name': f'beacon-{node_id}'
        },
        'spec': {
            'containers': [{
                'command': [
                    'sh',
                    '-ac',
                    f'''node /usr/app/node_modules/.bin/lodestar beacon --dataDir=/data --discv5 --listenAddress=0.0.0.0 --port=9000 --enr.ip=$(POD_IP) --enr.tcp=9000 --enr.udp=9000 --rest --rest.address=0.0.0.0 --rest.port=5052 --jwt-secret=/data/jwt.hex --metrics --metrics.address=0.0.0.0 --metrics.port=8008 --execution.urls={execution_client_uri} --genesisStateFile=/data/testnet_spec/genesis.ssz --paramsFile=/data/testnet_spec/config.yaml {bootnode_enr_cmd} --logLevel=debug --eth1 --targetPeers={target_peers} --metrics=true'''
                ],
                'image': 'chainsafe/lodestar:latest',
                'name': 'lodestar-container',
                'ports': [{'containerPort': 9000}, {'containerPort': 5052}, {'containerPort': 8008}],
                'volumeMounts': [
                    {'mountPath': '/data', 'name': 'storage'},
                    {'mountPath': '/data/jwt.hex', 'name': 'jwt', 'subPath': 'jwt.hex', 'readOnly': True}
                ],
                'env': [
                    {
                        'name': 'POD_IP',
                        'valueFrom': {'fieldRef': {'fieldPath': 'status.podIP'}}
                    }
                ],
                'readinessProbe': {
                    'failureThreshold': 3,
                    'initialDelaySeconds': 10,
                    'periodSeconds': 10,
                    'successThreshold': 1,
                    'tcpSocket': {'port': 5052}
                },
                'livenessProbe': {
                    'failureThreshold': 3,
                    'initialDelaySeconds': 60,
                    'periodSeconds': 120,
                    'successThreshold': 1,
                    'tcpSocket': {'port': 5052}
                },
                'resources': {
                    'limits': {
                        'cpu': '3',
                        'memory': '7Gi'
                    },
                    'requests': {
                        'cpu': '2',
                        'memory': '5Gi'
                    }
                }
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
                    'command': ['chown', '-R', '0:10001', '/data'],
                    'image': 'busybox:1.34.0',
                    'imagePullPolicy': 'IfNotPresent',
                    'name': 'init-chown-data',
                    'resources': {},
                    'volumeMounts': [{'mountPath': '/data', 'name': 'storage'}],
                    'securityContext': {'runAsUser': 0, 'runAsNonRoot': False}
                }
            ],
            'imagePullSecrets': [{'name': image_pull_secret}] if image_pull_secret else [],
            'volumes': [
                {'name': 'storage', 'emptyDir': {}},
                {'name': 'jwt', 'secret': {'secretName': 'jwt','defaultMode': 420}}
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
                'app.kubernetes.io/instance': f'beacon-{node_id}',
                'app.kubernetes.io/name': 'beacon',
                'consensus_client': 'lodestar',
                'ethereum_role': 'consensus',
                'node_id': str(node_id)
            },
            'name': f'beacon-{node_id}'
        },
        'spec': { 
            'ports': [
                {
                'name': 'p2p-udp',
                'port': 9000,
                'protocol': 'UDP',
                'targetPort': 9000
                },
                {
                'name': 'p2p-tcp',
                'port': 9000,
                'protocol': 'TCP',
                'targetPort': 9000
            }, {
                'name': 'rpc',
                'port': 5052,
                'protocol': 'TCP',
                'targetPort': 5052
            }, {
                'name': 'metrics',
                'port': 8008,
                'protocol': 'TCP',
                'targetPort': 8008
            }],
            'selector': {
                'app.kubernetes.io/instance': f'beacon-{node_id}',
                'app.kubernetes.io/name': 'beacon',
                'consensus_client': 'lodestar',
                'ethereum_role': 'consensus',
                'node_id': str(node_id)
            },
            'type': 'ClusterIP'
        }
    }

    # Create the Service
    api_response = api_instance.create_namespaced_service(namespace=namespace, body=service_manifest)

    return consensus_client_endpoints(
        HTTP_API_svc_endpoint=f'http://beacon-{node_id}.{namespace}.svc.cluster.local:5052',
        HTTP_API_ingress_endpoint=f'http://beacon-{node_id}.{namespace}.svc.cluster.local:5052',
        P2P_svc_endpoint=f'http://beacon-{node_id}.{namespace}.svc.cluster.local:30303',
        P2P_ingress_endpoint=f'http://beacon-{node_id}.{namespace}.svc.cluster.local:30303'
    )


def init_lodestar_validator(node_id,namespace,genesis_uri,beacon_node_uri,image_pull_secret=None):
    config.load_kube_config()

    api_instance = client.CoreV1Api()
    
    validator_manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'labels': {
                'app.kubernetes.io/instance': f'validator-{node_id}',
                'app.kubernetes.io/name': 'validator',
                'ethereum_role': 'validator'
            },
            'name': f'validator-{node_id}'
        },
        'spec': {
            'containers': [{
                'command': [
                    'sh',
                    '-ac',
                    f'''node /usr/app/node_modules/.bin/lodestar validator --dataDir=/data --beaconNodes={beacon_node_uri} --paramsFile=/data/testnet_spec/config.yaml --keystoresDir=/data/validator/keys --secretsDir=/data/validator/secrets --graffiti=$(hostname | cut -c -32) --logLevel=trace --metrics=true'''
                ],
                'image': 'chainsafe/lodestar:latest',
                'imagePullPolicy': 'IfNotPresent',
                'name': 'lodestar',
                'env': [
                    {
                        'name': 'POD_IP',
                        'valueFrom': {'fieldRef': {'fieldPath': 'status.podIP'}}
                    }
                ],
                'volumeMounts': [
                    {'mountPath': '/data', 'name': 'storage'},
                    {'mountPath': '/data/jwt.hex', 'name': 'jwt', 'subPath': 'jwt.hex', 'readOnly': True}
                ],
            }],
            'initContainers': [
                {
                    'command': [
                        'sh',
                        '-ace',
                    f'''while ! wget -T 5 -c {genesis_uri}/; do sleep 5; done; DEPOSIT_CONTRACT_URI={genesis_uri}/custom_config_data/deposit_contract.txt; DEPOSIT_CONTRACT_BLOCK_URI={genesis_uri}/custom_config_data/deposit_contract_block.txt; DEPLOY_BLOCK_URI={genesis_uri}/custom_config_data/deploy_block.txt; GENESIS_CONFIG_URI={genesis_uri}/custom_config_data/config.yaml; GENESIS_SSZ_URI={genesis_uri}/custom_config_data/genesis.ssz; TRUSTED_SETUP_URI={genesis_uri}/custom_config_data/trusted_setup.txt; mkdir -p /data/testnet_spec; apk update && apk add jq;
                    if ! [ -f /data/testnet_spec/genesis.ssz ]; then
                    wget -O /data/testnet_spec/deposit_contract.txt $DEPOSIT_CONTRACT_URI;
                    wget -O /data/testnet_spec/deposit_contract_block.txt $DEPOSIT_CONTRACT_BLOCK_URI;
                    wget -O /data/testnet_spec/deploy_block.txt $DEPLOY_BLOCK_URI;
                    wget -O /data/testnet_spec/config.yaml $GENESIS_CONFIG_URI;
                    wget -O /data/testnet_spec/genesis.ssz $GENESIS_SSZ_URI;
                    echo "genesis init done";

                    else
                        echo "genesis exists. skipping...";
                    fi;
                    '''],
                    'image': 'alpine:latest',
                    'imagePullPolicy': 'IfNotPresent',
                    'name': 'init-genesis',
                    'volumeMounts': [{'mountPath': '/data', 'name': 'storage'}],
                    'resources': {},
                    'securityContext': {'runAsUser': 0, 'runAsNonRoot': False}
                },
                {
                    'name':'init-keys',
                    'image':'kataak/eth-genesis:latest',
                    'imagePullPolicy':'IfNotPresent',
                    'volumeMounts': [{'mountPath': '/data', 'name': 'storage'}],
                    'resources': {},
                    'securityContext': {'runAsUser': 0, 'runAsNonRoot': False},
                    'command': [
                        'bash',
                        '-ace',
                        f'''if [ -n "$(ls -A /data/validator/keys 2>/dev/null)" ]; then
                        echo "keys already exist. skipping..."; exit 0;
                        fi;
                        EXTRACTED_MNEMONIC=$(echo "$MNEMONIC" | awk -F": " '/mnemonic:/ {{print $2}}');
                        INDEX=$(echo $(hostname) | rev | cut -d'-' -f 1 | rev);
                        RANGE="NODE_${{INDEX}}_KEY_RANGE";
                        S_MIN=$(echo ${{!RANGE}}| cut -d ':' -f1 );
                        S_MAX=$(echo ${{!RANGE}} | cut -d ':' -f2 );
                        mkdir -p /data/validator/keys /data/validator/secrets;
                        echo "generating keys for node $INDEX. range $S_MIN to $S_MAX";
                        eth2-val-tools keystores --source-mnemonic="$MNEMONIC" --source-min=$S_MIN --source-max=$S_MAX --prysm-pass Pass123word --insecure --out-loc assigned_data;
                        mv assigned_data/keys/* /data/validator/keys/;
                        mv assigned_data/secrets/* /data/validator/secrets/;
                        chmod -R 0600 /data/validator/keys/*/voting-keystore.json /data/validator/secrets/*;
                        echo "finished generating and importing keys";'''
                    ],
                    'env': [
                    # {
                    #     'name': 'MNEMONIC',
                    #     'valueFrom': {
                    #         'configMapKeyRef': {
                    #             'name': 'eth-genesis-cl',
                    #             'key': 'mnemonics.yaml'
                    #         }
                    #     }
                    # },
                    {
                        'name':'MNEMONIC',
                        'value': 'sleep moment list remain like wall lake industry canvas wonder ecology elite duck salad naive syrup frame brass utility club odor country obey pudding'
                    },
                    {
                        'name': 'NODE_0_KEY_RANGE',
                        'value':'0:4000'
                    },
                    {
                        'name': 'NODE_1_KEY_RANGE',
                        'value':'4001:8000'
                    }
                ],
                },
                {
                    'command': ['chown', '-R', '10001:10001', '/data'],
                    'image': 'busybox:1.34.0',
                    'imagePullPolicy': 'IfNotPresent',
                    'name': 'init-chown-data',
                    'resources': {},
                    'volumeMounts': [{'mountPath': '/data', 'name': 'storage'}],
                    'securityContext': {'runAsUser': 0, 'runAsNonRoot': False}
                },
                {
                'name':'init-beacon-wait',
                'image':'alpine:latest',
                'imagePullPolicy':'IfNotPresent',
                'securityContext':{'runAsUser':0,'runAsNonRoot':False},
                'resources':{},
                'volumeMounts':[{'mountPath':'/data','name':'storage'}],
                'command':[
                        'sh',
                        '-ac',
                        f'''HEALTH_API="{beacon_node_uri}/eth/v1/node/identity"; echo "waiting for beacon node to be available on $HEALTH_API"; while ! wget $HEALTH_API; do sleep 10; done; echo "beacon node is available"'''
                ],
                }

            ],
            'volumes': [
                {'name': 'storage', 'emptyDir': {}},
                {'name': 'jwt', 'secret': {'secretName': 'jwt','defaultMode': 420}}
            ],
            'securityContext': {
                'fsGroup': 10001,
                'runAsGroup': 10001,
                'runAsUser': 10001,
                'runAsNonRoot': True
            },
         'imagePullSecrets': [{'name': image_pull_secret}] if image_pull_secret else [],

        }
    }
    api_response = api_instance.create_namespaced_pod(namespace=namespace, body=validator_manifest)

    return {
        'validator_id': node_id,
        'validator_name': 'lodestar',
        'validator_namespace': namespace,
    }