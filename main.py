

from ethereum.eth_chain import EthChain


eth_network_spec = {
  'namespace':'3',
  'genesis':{
        'chain_id':'13372345',
        'deposit_contract_address':'0x6f22fFbC56eFF051aECF839396DD1eD9aD6BBA9D',
        'el_and_cl_mnemonic':"sleep moment list remain like wall lake industry canvas wonder ecology elite duck salad naive syrup frame brass utility club odor country obey pudding",
        'slot_duration_in_seconds':12,
        'deposit_contract_block':"0x0000000000000000000000000000000000000000000000000000000000000000",
        'number_of_validators':320,
        'genesis_fork_version':"0x10000000",
        'altair_fork_version':"0x20000000",
        'bellatrix_fork_version':"0x30000000",
        'capella_fork_version':"0x40000000",
        'deneb_fork_version':"0x50000000",
        'deneb_fork_epoch':'20000',
        'withdrawl_type':'0x00',
        'withdrawl_address':0xf97e180c050e5Ab072211Ad2C213Eb5AEE4DF134,
        'beacon_static_enr':'',
        'genesis_timestamp':0,
        'genesis_delay':60
    },
    'nodes': [
      {'execution_client': 'nethermind', 'consensus_client': 'lodestar'},
      {'execution_client': 'nethermind', 'consensus_client': 'lodestar'},
      {'execution_client': 'nethermind', 'consensus_client': 'lodestar'},
    ],
    'validators': [
      {'validator': 'lodestar', 'beacon_node_id': 0},
      {'validator': 'lodestar', 'beacon_node_id': 1}
    ]
}

ethChain = EthChain(eth_network_spec)
print(ethChain.nodes)
ethChain.init_faucet_wallet()
