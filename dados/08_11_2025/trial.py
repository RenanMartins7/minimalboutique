import optuna
import time
import hashlib
import json
import yaml
import math
from kubernetes import client, config
from agent import ReinforceAgent
from history import *
from es_utils import *

# --- Carrega config Kubernetes (ajuste se necessário) ---
config.load_incluster_config()
apps_v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()

NAMESPACE = "rmalves"
DEPLOYMENT_NAME = "collector"
CONFIGMAP_NAME = "collector-config"
POLICIES_FILE = "tail_sampling_policies.json"

NUM_OF_EPISODES = 10


# --- Funções auxiliares (iguais às suas) ---
def generate_config(selected_policies, config_hash):
    config_dict = {
        "receivers": {"otlp": {"protocols": {"http": {"endpoint": "0.0.0.0:4321"}}}},
        "processors": {
            "tail_sampling": {
                "decision_wait": "10s",
                "num_traces": 10000,
                "expected_new_traces_per_sec": 500,
                "policies": selected_policies
            },
            "attributes": {
                "actions": [
                    {"key": "experiment_hash", "value": config_hash, "action": "insert"}
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
                "metrics": {"receivers": ["otlp"], "exporters": ["prometheus"]}
            }
        }
    }
    return yaml.dump(config_dict)


def update_configmap(config_yaml):
    cm_body = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=CONFIGMAP_NAME, namespace=NAMESPACE),
        data={"config.yaml": config_yaml}
    )
    try:
        core_v1.replace_namespaced_config_map(CONFIGMAP_NAME, NAMESPACE, cm_body)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            core_v1.create_namespaced_config_map(NAMESPACE, cm_body)
        else:
            raise


def rolling_update_deployment(config_yaml, config_hash):
    patch = {"spec": {"template": {"metadata": {"annotations": {"config-hash": config_hash}}}}}
    apps_v1.patch_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=patch)


def wait_for_rollout_ready():
    while True:
        deployment = apps_v1.read_namespaced_deployment(DEPLOYMENT_NAME, NAMESPACE)
        desired = deployment.spec.replicas
        available = deployment.status.available_replicas or 0
        if available >= desired:
            return
        time.sleep(2)


def trace_penalty_function(traces, C, k=25, midpoint=0.10):
    x = traces / C
    return 1 / (1 + math.exp(-k * (x - midpoint)))


def reward_function(entropy, traces, alpha=1.0, beta=1.2, C=12000):
    norm_entropy = entropy / 10
    trace_penalty = trace_penalty_function(traces, C)
    return alpha * norm_entropy - beta * trace_penalty


# --- Objetivo para o Optuna ---
def objective(trial):
    # 🔧 Optuna vai sugerir valores
    alpha = trial.suggest_float("alpha", 0.1, 3.0)
    beta = trial.suggest_float("beta", 0.1, 3.0)

    # Carrega políticas e agente
    with open(POLICIES_FILE, "r") as f:
        all_policies = json.load(f)

    agent = ReinforceAgent(num_policies=len(all_policies))
    first = True
    total_reward = 0

    # roda poucos ciclos por trial (ex: 3 iterações)
    for _ in range(NUM_OF_EPISODES):
        if first:
            old_hash = "init"
            first = False
        else:
            old_hash = config_hash

        selected_policies = agent.select_actions(all_policies)
        selected_policies.append({
            "name": "default-probabilistic-policy",
            "type": "probabilistic",
            "probabilistic": {"sampling_percentage": 0.1}
        })

        policies_str = json.dumps(selected_policies, sort_keys=True)
        timestamp = str(time.time())
        config_hash = hashlib.sha256((policies_str + timestamp).encode()).hexdigest()[:8]
        config_yaml = generate_config(selected_policies, config_hash)

        update_configmap(config_yaml)
        rolling_update_deployment(config_yaml, config_hash)
        wait_for_rollout_ready()

        # Coleta métricas e calcula reward
        entropy, num_traces = export_traces_by_hash(old_hash)
        reward = reward_function(entropy, num_traces, alpha=alpha, beta=beta)

        total_reward += reward

        agent.update(selected_policies, reward)
        time.sleep(60)  # tempo para o coletor estabilizar

    avg_reward = total_reward / NUM_OF_EPISODES
    print(f"[Trial] alpha={alpha:.3f}, beta={beta:.3f} -> reward={avg_reward:.4f}")
    return avg_reward


# --- Roda o Optuna ---
if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=30)

    print("✅ Melhor resultado:")
    print(study.best_params)
    print(f"Melhor recompensa média: {study.best_value:.4f}")
