import time
import hashlib
from kubernetes import client, config
import json
import random
import yaml
import os
from history import *
from es_utils import *

config.load_incluster_config()
apps_v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()

NAMESPACE = "rmalves"
DEPLOYMENT_NAME = "collector"
CONFIGMAP_NAME = "collector-config"
POLICIES_FILE = "tail_sampling_policies.json"

def generate_config():
    with open(POLICIES_FILE, "r") as f:
        all_policies = json.load(f)

    num_policies_to_select = random.randint(1, len(all_policies))
    selected_policies = random.sample(all_policies, num_policies_to_select)

    # Sempre adiciona um default para não perder tudo
    selected_policies.append({
        "name": "default-probabilistic-policy",
        "type": "probabilistic",
        "probabilistic": {"sampling_percentage": 100.0}
    })

    print(f"Políticas selecionadas para esta iteração: {[p['name'] for p in selected_policies]}")

    # Calcula hash único baseado nas políticas
    policies_str = json.dumps(selected_policies, sort_keys=True)
    config_hash = hashlib.sha256(policies_str.encode()).hexdigest()[:8]

    # Monta configuração do coletor
    config_dict = {
        "receivers": {
            "otlp": {
                "protocols": {
                    "http": {"endpoint": "0.0.0.0:4321"}
                }
            }
        },
        "processors": {
            "tail_sampling": {
                "decision_wait": "10s",
                "num_traces": 2000,
                "expected_new_traces_per_sec": 100,
                "policies": selected_policies
            },
            # 🔹 Injeta o hash como atributo em cada trace
            "attributes": {
                "actions": [
                    {
                        "key": "experiment.hash",
                        "value": config_hash,
                        "action": "insert"
                    }
                ]
            }
        },
        "exporters": {
            "debug": {"verbosity": "detailed"},
            "otlphttp": {"endpoint": "http://jaeger:4318"},
            "prometheus": {"endpoint": "0.0.0.0:9464"}
        },
        "service": {
            "pipelines": {
                "traces": {
                    "receivers": ["otlp"],
                    "processors": ["tail_sampling", "attributes"],
                    "exporters": ["otlphttp"]
                },
                "metrics": {
                    "receivers": ["otlp"],
                    "exporters": ["prometheus"]
                }
            }
        }
    }

    return yaml.dump(config_dict), config_hash, selected_policies


def update_configmap(config_yaml):
    cm_body = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=CONFIGMAP_NAME, namespace=NAMESPACE),
        data={"config.yaml": config_yaml}
    )
    try:
        core_v1.replace_namespaced_config_map(CONFIGMAP_NAME, NAMESPACE, cm_body)
        print(f"ConfigMap {CONFIGMAP_NAME} updated")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            core_v1.create_namespaced_config_map(NAMESPACE, cm_body)
            print(f"ConfigMap {CONFIGMAP_NAME} created")
        else:
            raise


def rolling_update_deployment(config_yaml, config_hash):
    patch = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "config-hash": config_hash
                    }
                }
            }
        }
    }
    apps_v1.patch_namespaced_deployment(
        name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=patch
    )
    print(f"Deployment {DEPLOYMENT_NAME} patched with config hash {config_hash}")


def wait_for_rollout_ready():
    while True:
        deployment = apps_v1.read_namespaced_deployment(DEPLOYMENT_NAME, NAMESPACE)
        desired = deployment.spec.replicas
        available = deployment.status.available_replicas or 0
        if available >= desired:
            print("Rollout completo!")
            return
        print(f"Aguardando rollout... {available}/{desired} prontos")
        time.sleep(5)

if __name__ == "__main__":
    while True:
        config_yaml, config_hash, selected_policies = generate_config()

        update_configmap(config_yaml)

        rolling_update_deployment(config_yaml, config_hash)

        print("Waiting for new pod to be ready...")
        wait_for_rollout_ready()
        print("New pod ready!")

        save_history(config_hash, selected_policies)
        json_file = export_traces_by_hash(config_hash)
        print(f"Arquivo de traces salvo localmente: {json_file}")

        time.sleep(60)
