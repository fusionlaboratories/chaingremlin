

from dataclasses import dataclass


@dataclass
class Node:
  namespace: str
  node_id: int
  p2p_svc_endpoint: str 
  p2p_ingress_endpoint:str


class BTCsignet:
  
  def __init__(self):
    self.namespace=""
    self.signet_challenge=""
    self.nodes=[]

