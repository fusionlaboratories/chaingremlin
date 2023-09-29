from dataclasses import dataclass
import os 
import yaml 
import kubernetes import client, config 


class BTC_signet:
  def __init__(self,name, namespace):
    self.name = name 
    self.namespace = namespace
    self.nodes = []

  @dataclass
  class node:
    rpcuser: str 
    rpcpassword: str
    namespace: str

  def init_nodes(self):
    pass

  def deploy_to_kubernetes(self):
    pass
  