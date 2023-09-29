import os
from kubernetes import client, config

class ChaosMeshClient:
    def __init__(self):
        # Load the Kubernetes configuration from the default location
        config.load_kube_config()

        # Initialize the Kubernetes API client
        self.api_client = client.ApiClient()
        self.core_api = client.CoreV1Api(self.api_client)

    def create_network_attack(self, experiment_yaml):
        try:
            chaos_api = client.CustomObjectsApi(self.api_client)
            chaos_api.create_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace="your-namespace",
                plural="networkchaos",
                body=experiment_yaml
            )
            print("Network attack experiment created successfully.")
        except Exception as e:
            print(f"Error creating network attack experiment: {str(e)}")

    def list_experiments(self, namespace, label_selector=None):
        try:
            api_instance = client.CustomObjectsApi(self.api_client)
            label_selector = label_selector or ""
            experiments = api_instance.list_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace=namespace,
                plural="networkchaos",
                label_selector=label_selector
            )
            return experiments.get("items", [])
        except Exception as e:
            print(f"Error listing network attack experiments: {str(e)}")

    def delete_experiment(self, namespace, name):
        try:
            chaos_api = client.CustomObjectsApi(self.api_client)
            chaos_api.delete_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace=namespace,
                plural="networkchaos",
                name=name
            )
            print(f"Network attack experiment '{name}' deleted successfully.")
        except Exception as e:
            print(f"Error deleting network attack experiment: {str(e)}")

# Usage example
if __name__ == "__main__":
    chaos_client = ChaosMeshClient()

    # Example: Create a network attack experiment
    experiment_yaml = """
    
    """
    chaos_client.create_network_attack(experiment_yaml)

    # Example: List experiments in a namespace with a label selector
    experiments = chaos_client.list_experiments(namespace="your-namespace", label_selector="app=example")
    print("List of experiments:")
    for experiment in experiments:
        print(experiment)

    # Example: Delete an experiment by name
    experiment_name = "example-experiment"
    chaos_client.delete_experiment(namespace="your-namespace", name=experiment_name)
