

from dataclasses import dataclass


@dataclass
class execution_client_endpoints:
  http_rpc_svc_endpoint: str
  http_rpc_ingress_endpoint:str  
  auth_rpc_svc_endpoint: str
  auth_rpc_ingress_endpoint: str

@dataclass
class consensus_client_endpoints:
  HTTP_API_svc_endpoint: str
  HTTP_API_ingress_endpoint:str  
  P2P_svc_endpoint: str
  P2P_ingress_endpoint: str 

@dataclass
class ethereum_node:
  node_id: int
  node_name: str
  namespace: str
  execution_client_endpoints: execution_client_endpoints
  consensus_client_endpoints: consensus_client_endpoints


#class eth_node_rss_quota: