

from ast import List
import string
from chaos_mesh.network_attack import ChaosMeshClient
from ethereum.genesis import init_genesis
from ethereum.lodestar import init_lodestar, init_lodestar_validator
from ethereum.models import ethereum_node
from ethereum.nethermind import init_nethermind
from ethereum.wallet import EthereumWallet
from ethereum.ingress import create_ingress_resource


class EthChain():
  namespace = string 
  chain_id = int
  genesis_uri = str
  nodes = list 
  validators = list
  faucet = EthereumWallet

  def __init__(self, chain_spec):
    self.namespace = chain_spec['namespace']
    self.chain_id = chain_spec['genesis']['chain_id']
    self.genesis_uri = init_genesis(chain_spec)
    self.nodes = self.init_nodes(chain_spec) 
    self.validators = self.init_validators(chain_spec)
    #self.chaos_client=ChaosMeshClient()
   

  def init_faucet_wallet(self):
    self.faucet = EthereumWallet(self.nodes[0].execution_client_endpoints.http_rpc_ingress_endpoint)

  def init_nodes(self,chain_spec):
    nodes = []
    for nid,node in enumerate(chain_spec['nodes']):
      if nid == 0:
        execution_client_endpoints = init_nethermind(self.namespace,nid,self.genesis_uri)
        consensus_client_endpoints = init_lodestar(self.namespace,
                                                  nid,
                                                  self.genesis_uri,
                                                  len(chain_spec)-1,
                                                  execution_client_endpoints.http_rpc_svc_endpoint,
                                                  )

        nodes.append(create_ingress_resource(ethereum_node(
          node_id = nid,
          node_name = node['execution_client'],
          namespace = chain_spec['namespace'],
          execution_client_endpoints = execution_client_endpoints,
          consensus_client_endpoints = consensus_client_endpoints
          )
        ))

      else:
        execution_client_endpoints = init_nethermind(self.namespace,
                                                    nid,
                                                    self.genesis_uri,
                                                    bootnode_svc_endpoint=nodes[0].execution_client_endpoints.http_rpc_svc_endpoint
        )
        consensus_client_endpoints = init_lodestar(self.namespace,
                                                  nid,
                                                  self.genesis_uri,
                                                  len(chain_spec)-1,
                                                  execution_client_endpoints.http_rpc_svc_endpoint,
                                                  beacon_bootnode_uri=nodes[0].consensus_client_endpoints.HTTP_API_svc_endpoint
                                                  )
        
        node_obj = ethereum_node(
          node_id = nid,
          node_name = node['execution_client'],
          namespace = chain_spec['namespace'],
          execution_client_endpoints = execution_client_endpoints,
          consensus_client_endpoints = consensus_client_endpoints
        )
        patched_node_obj=create_ingress_resource(node_obj)
        nodes.append(patched_node_obj
      )
    return nodes

  def init_validators(self,chain_spec):
    validators = []
    for vid,validator in enumerate(chain_spec['validators']):
      v = init_lodestar_validator(vid,self.namespace,self.genesis_uri,self.nodes[validator['beacon_node_id']].consensus_client_endpoints.HTTP_API_svc_endpoint,chain_spec['genesis']['el_and_cl_mnemonic'])
      validators.append(v)
    return validators


  def fund(self,target_address,amount):
    if self.faucet != None:
      self.faucet.transfer(amount,target_address)
    else:
      self.init_faucet_wallet(self)
      self.faucet.transfer(amount,target_address)

    