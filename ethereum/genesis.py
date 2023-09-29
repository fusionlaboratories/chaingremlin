from kubernetes import client,config
from kubernetes.client.api import core_v1_api

import time
import yaml


eth_cl_genesis = {
      'PRESET_BASE': 'mainnet',
      'CONFIG_NAME': 'testnet', # needs to exist because of Prysm. Otherwise it conflicts with mainnet genesis
      'MIN_GENESIS_ACTIVE_VALIDATOR_COUNT': '$NUMBER_OF_VALIDATORS',
      'MIN_GENESIS_TIME': '$GENESIS_TIMESTAMP',
      'GENESIS_FORK_VERSION': '$GENESIS_FORK_VERSION',
      'GENESIS_DELAY':' $GENESIS_DELAY',
      'ALTAIR_FORK_VERSION': '$ALTAIR_FORK_VERSION',
      'ALTAIR_FORK_EPOCH': 0,
      'BELLATRIX_FORK_VERSION': '$BELLATRIX_FORK_VERSION',
      'BELLATRIX_FORK_EPOCH': 0,
      'TERMINAL_TOTAL_DIFFICULTY': 0,
      'TERMINAL_BLOCK_HASH': '0x0000000000000000000000000000000000000000000000000000000000000000',
      'TERMINAL_BLOCK_HASH_ACTIVATION_EPOCH': 18446744073709551615,
      'CAPELLA_FORK_VERSION': '$CAPELLA_FORK_VERSION',
      'CAPELLA_FORK_EPOCH': 0,
      'DENEB_FORK_VERSION': '$DENEB_FORK_VERSION',
      'DENEB_FORK_EPOCH': '$DENEB_FORK_EPOCH',
      'SECONDS_PER_SLOT': '$SLOT_DURATION_IN_SECONDS',
      'SECONDS_PER_ETH1_BLOCK': '$SLOT_DURATION_IN_SECONDS',
      'MIN_VALIDATOR_WITHDRAWABILITY_DELAY': 1,
      'SHARD_COMMITTEE_PERIOD': 1,
      'ETH1_FOLLOW_DISTANCE': 12,
      'INACTIVITY_SCORE_BIAS': 4,
      'INACTIVITY_SCORE_RECOVERY_RATE': 16,
      'EJECTION_BALANCE': 31000000000,
      'MIN_PER_EPOCH_CHURN_LIMIT': 4,
      'CHURN_LIMIT_QUOTIENT': 65536,
      'PROPOSER_SCORE_BOOST': 40,
      'DEPOSIT_CHAIN_ID': '$CHAIN_ID',
      'DEPOSIT_NETWORK_ID': '$CHAIN_ID',
      'DEPOSIT_CONTRACT_ADDRESS': '$DEPOSIT_CONTRACT_ADDRESS',
      'GOSSIP_MAX_SIZE': 10485760,
      'MAX_REQUEST_BLOCKS': 1024,
      'EPOCHS_PER_SUBNET_SUBSCRIPTION': 256,
      'MIN_EPOCHS_FOR_BLOCK_REQUESTS': 33024,
      'MAX_CHUNK_SIZE': 10485760,
      'TTFB_TIMEOUT': 5,
      'RESP_TIMEOUT': 10,
      'ATTESTATION_PROPAGATION_SLOT_RANGE': 32,
      'MAXIMUM_GOSSIP_CLOCK_DISPARITY': 500,
      'MESSAGE_DOMAIN_INVALID_SNAPPY': 0x00000000,
      'MESSAGE_DOMAIN_VALID_SNAPPY': 0x01000000,
      'SUBNETS_PER_NODE': 2,
      'ATTESTATION_SUBNET_COUNT': 64,
      'ATTESTATION_SUBNET_EXTRA_BITS': 0,
      'ATTESTATION_SUBNET_PREFIX_BITS': 6,
      'MAX_REQUEST_BLOCKS_DENEB': 128,
      'MAX_REQUEST_BLOB_SIDECARS': 768,
      'MIN_EPOCHS_FOR_BLOB_SIDECARS_REQUESTS': 4096,
      'BLOB_SIDECAR_SUBNET_COUNT': 6,
      'MAX_BLOBS_PER_BLOCK': 6
} 
genesis_http_server_pod_spec = {
    'apiVersion': 'v1',
    'kind': 'Pod',
    'metadata': {
        'name': 'ethereum-genesis-generator',
        'labels': {
            'app': 'ethereum-genesis-generator'
        }
    },
    'spec': {
        'containers': [
            {
                'name': 'ethereum-genesis-generator',
                'image': 'kataak/ethereum-genesis-generator:latest',
                'imagePullPolicy': 'IfNotPresent',
                'args': ['all'],
                'volumeMounts': [
                    {'name': 'storage', 'mountPath': '/data'},
                    {'name': 'config-el', 'mountPath': '/config/el', 'readOnly': True},
                    {'name': 'config-cl', 'mountPath': '/config/cl', 'readOnly': True}
                ],
                'env': [
                    {'name': 'SHADOW_FORK_RPC', 'value': ''},
                    {'name': 'SERVER_ENABLED', 'value': 'true'}
                ],
                'ports': [{'name': 'http', 'containerPort': 8000, 'protocol': 'TCP'}]
            }
        ],
        'initContainers': [
            {
                'name': 'init-chown-data',
                'image': 'busybox:1.34.0',
                'imagePullPolicy': 'IfNotPresent',
                'securityContext': {
                    'runAsNonRoot': False,
                    'runAsUser': 0
                },
                'command': ['chown', '-R', '10001:10001', '/data'],
                'resources': {
                    'limits': {'cpu': '100m', 'memory': '128Mi'},
                    'requests': {'cpu': '100m', 'memory': '128Mi'}
                },
                'volumeMounts': [{'name': 'storage', 'mountPath': '/data'}],
                'ports': [{'name': 'http', 'containerPort': 8000, 'protocol': 'TCP'}]
            }
        ],
        'securityContext': {
            'fsGroup': 10001,
            'runAsGroup': 10001,
            'runAsNonRoot': True,
            'runAsUser': 10001
        },
        'volumes': [
            {'name': 'config-el', 'configMap': {'name': 'eth-genesis-el'}},
            {'name': 'config-cl', 'configMap': {'name': 'eth-genesis-cl'}},
            {'name': 'storage', 'emptyDir': {}}
        ]
    }
}


def create_jwt_secret():
  return {
    'apiVersion': 'v1',
    'kind': 'Secret',
    'metadata': {
       'name': 'jwt'
    },
    'type': 'Opaque',
    'data': {
      'jwt.hex': 'ZWNiMjJiYzI0ZTdkNDA2MWY3ZWQ2OTBjY2Q1ODQ2ZDdkNzNmNWQyYjk3MzMyNjdlMTJmNTY3OTAzOThkOTA4YQ=='
    }
  }

def create_genesis_svc(genesis_pod_name):
    return {
      'apiVersion': 'v1',
      'kind': 'Service',
      'metadata': {
        'name': genesis_pod_name
      },
      'spec': {
        'type': 'ClusterIP',
        'ports': [{
            'port': 8000,
            'targetPort': 'http',
            'protocol': 'TCP',
            'name': 'http'
        }],
        'selector': {
          'app': genesis_pod_name
      }
  }
}

def init_el_configmapt(genesis_spec):
    genesis_config = {
        'chain_id': genesis_spec['chain_id'],
        'deposit_contract_address': genesis_spec['deposit_contract_address'],
        'mnemonic': genesis_spec['el_and_cl_mnemonic'],
        'el_premine': {
            "m/44'/60'/0'/0/1": '1000000000ETH',
            "m/44'/60'/0'/0/2": '1000000000ETH',
            "m/44'/60'/0'/0/3": '1000000000ETH',
            "m/44'/60'/0'/0/4": '1000000000ETH',
            "m/44'/60'/0'/0/5": '1000000000ETH'
        },
        'el_premine_addrs': {},
        'genesis_timestamp': genesis_spec['genesis_timestamp'],
        'genesis_delay': genesis_spec['genesis_delay'],
        'slot_duration_in_seconds': genesis_spec['slot_duration_in_seconds'],
        'deneb_fork_epoch': genesis_spec['deneb_fork_epoch']
    }

    return {
        'apiVersion': 'v1',
        'kind': 'ConfigMap',
        'metadata': {'name': 'eth-genesis-el'},
        'data': {
            'genesis-config.yaml': yaml.dump(genesis_config, default_flow_style=False)
        }
    }
            



def init_cl_configmap(genesis_config):
    cl_genesis_cm = eth_cl_genesis.copy()
    
    cl_fields = [
        'MIN_GENESIS_ACTIVE_VALIDATOR_COUNT', 'MIN_GENESIS_TIME',
        'GENESIS_FORK_VERSION', 'GENESIS_DELAY', 'ALTAIR_FORK_VERSION',
        'BELLATRIX_FORK_VERSION', 'CAPELLA_FORK_VERSION', 'DENEB_FORK_VERSION',
        'DENEB_FORK_EPOCH', 'SECONDS_PER_SLOT', 'SECONDS_PER_ETH1_BLOCK',
        'DEPOSIT_CHAIN_ID', 'DEPOSIT_CONTRACT_ADDRESS'
    ]
    
    for field in cl_fields:
        try:
            cl_genesis_cm[field] = genesis_config[field.lower()]
        except KeyError:
            pass
    
    mnemonics = [{'mnemonic': genesis_config['el_and_cl_mnemonic'],
                  'count': genesis_config['number_of_validators']}]
    
    cl_yaml = yaml.dump(cl_genesis_cm, default_flow_style=False)
    mnemonics_yaml = yaml.dump(mnemonics, default_flow_style=False)

    
    return {
        'apiVersion': 'v1',
        'kind': 'ConfigMap',
        'metadata': {'name': 'eth-genesis-cl'},
        'data': {
            'config.yaml': cl_yaml,
            'mnemonics.yaml': mnemonics_yaml
        }
    }


def init_genesis(chain_spec,recreate_resources=False, genesis_pod_name='eth-genesis'):
    print("Initializing genesis")
    genesis_spec=chain_spec['genesis'] 
    namespace=chain_spec['namespace']
    config.load_kube_config()
    core_v1 = core_v1_api.CoreV1Api()
    try: core_v1_api.CoreV1Api().create_namespace({'apiVersion':'v1','kind':'Namespace','metadata':{'name':namespace,'kubernetes.io/metadata.name':namespace}})
    except client.exceptions.ApiException:
        print("Namespace already exists")
        pass
    genesis_spec['genesis_timestamp'] = int(time.time())

    
    el_cm = init_el_configmapt(genesis_spec)
    cl_cm = init_cl_configmap(genesis_spec)
    jwt = create_jwt_secret()
    genesis_http_server_svc_manifest = create_genesis_svc(genesis_pod_name)

    genesis_http_server_manifest = genesis_http_server_pod_spec.copy()
    genesis_http_server_manifest['metadata']['name'] = genesis_pod_name
    genesis_http_server_manifest['metadata']['labels']['app'] = genesis_pod_name
    
    resources_to_create = [
        (core_v1.create_namespaced_pod, genesis_http_server_manifest, namespace),
        (core_v1.create_namespaced_secret, jwt, namespace),
        (core_v1.create_namespaced_config_map, cl_cm, namespace),
        (core_v1.create_namespaced_config_map, el_cm, namespace),
        (core_v1.create_namespaced_service, genesis_http_server_svc_manifest, namespace)
    ]

    for create_resource, resource_body, resource_namespace in resources_to_create:
        try:
            create_resource(body=resource_body, namespace=resource_namespace)
        except client.exceptions.ApiException:
            # if recreate_resources:
            #     try: 
            #         core_v1.delete_namespaced_pod(name=genesis_pod_name, namespace=namespace)
            #     except client.exceptions.ApiException:
            #         pass
            #     try: 
            #         core_v1.delete_namespaced_secret(name=jwt['metadata']['name'], namespace=namespace)
            #     except client.exceptions.ApiException:
            #         pass
            #     try: 
            #         core_v1.delete_namespaced_config_map(name=el_cm['metadata']['name'], namespace=namespace)
            #     except client.exceptions.ApiException:
            #         pass
            #     try: 
            #         core_v1.delete_namespaced_config_map(name=cl_cm['metadata']['name'], namespace=namespace)
            #     except client.exceptions.ApiException:
            #         pass
            #     try: 
            #         core_v1.delete_namespaced_service(name=genesis_http_server_svc_manifest['metadata']['name'], namespace=namespace)
            #     except client.exceptions.ApiException:
            #         pass
            # else: 
            #     print(client.exceptions.ApiException)
            #     pass  # TODO: Handle exception
            print(client.exceptions.ApiException)
            pass

    while True:
        resp = core_v1.read_namespaced_pod(name=genesis_pod_name, namespace=namespace)
        if resp.status.phase == 'Running':
            return 'http://'+f'{genesis_pod_name}.{namespace}.svc.cluster.local:8000'
