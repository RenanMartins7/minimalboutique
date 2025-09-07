import time
import hashlib
from kubernetes import client, config


config.load_incluster_config() 
apps_v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()

NAMESPACE = "rmalves"
DEPLOYMENT_NAME = "collector"
CONFIGMAP_NAME = "collector-config"

def generate_config():
    """Gera dinamicamente a configuração do collector"""

    return """
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4321
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 2000
    expected_new_traces_per_sec: 100
    policies:
      - name: probability-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 100.0
exporters:
  debug:
    verbosity: detailed
  otlphttp:
    endpoint: http://jaeger:4318
  prometheus:
    endpoint: "0.0.0.0:9464"
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [tail_sampling]
      exporters: [otlphttp]
    metrics:
      receivers: [otlp]
      exporters: [prometheus]
"""

def update_configmap(config_yaml):
    """Atualiza ou cria ConfigMap"""
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

def rolling_update_deployment(config_yaml):
    """Faz rolling update usando annotation com hash da config"""
    config_hash = hashlib.sha256(config_yaml.encode()).hexdigest()[:8]
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
    apps_v1.patch_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=patch)
    print(f"Deployment {DEPLOYMENT_NAME} patched with config hash {config_hash}")

def wait_for_pod_ready(label_selector):
    while True:
        pods = core_v1.list_namespaced_pod(namespace=NAMESPACE, label_selector=label_selector)
        if pods.items and all([c.status.phase == "Running" for c in pods.items]):
            ready = True
            for pod in pods.items:
                for cs in pod.status.container_statuses or []:
                    if not cs.ready:
                        ready = False
            if ready:
                return

if __name__ == "__main__":
    while True:
        config_yaml = generate_config()

        update_configmap(config_yaml)

        rolling_update_deployment(config_yaml)

        print("Waiting for new pod to be ready...")
        wait_for_pod_ready("app=collector")
        print("New pod ready!")
        time.sleep(30)


