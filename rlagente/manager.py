import time
import hashlib
from kubernetes import client, config
import json
import random
import yaml
import os
from history import *
from es_utils import *
#Configuração inicial
#######################################################################################################################################
config.load_incluster_config()#Script roda no próprio cluster, então configuração é incluster
apps_v1 = client.AppsV1Api()#Definição de objetos para manipular os deployments
core_v1 = client.CoreV1Api()#Definição de objetos para manipular os configmaps
#Definição das constantes a serem usadas
NAMESPACE = "rmalves"
DEPLOYMENT_NAME = "collector"
CONFIGMAP_NAME = "collector-config"
POLICIES_FILE = "tail_sampling_policies.json"
#######################################################################################################################################
#Gera o arquivo de configurações do coletor
def generate_config():
    with open(POLICIES_FILE, "r") as f:#Abre o arquivo que contem todas as possíveis regras para serem aplicadas no tailsampling 
        all_policies = json.load(f)

    num_policies_to_select = random.randint(1, len(all_policies))#Seleciona aleatoriamente um número de políticas a serem adicionadas ao coletor
    selected_policies = random.sample(all_policies, num_policies_to_select)#Seleciona aleatóriamente o número de políticas acima para ser adicionado no configmap

    
    selected_policies.append({#coloca uma política default que pega uma porcentagem dos traces para garantir que uma porcentagem é sampleada mesmo que não caia nas regras
        "name": "default-probabilistic-policy",
        "type": "probabilistic",
        "probabilistic": {"sampling_percentage": 10.0}
    })

    # print(f"Políticas selecionadas para esta iteração: {[p['name'] for p in selected_policies]}")

    policies_str = json.dumps(selected_policies, sort_keys=True)#Gera o arquivo com as políticas selecionadas no formato json
    config_hash = hashlib.sha256(policies_str.encode()).hexdigest()[:8]#Gera a hash que representa as políticas selecionadas a partir do arquivo gerado com elas 

    
    config_dict = {# Monta configuração do coletor
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
            
            "attributes": {# 🔹 Injeta o hash como atributo em cada trace
                "actions": [
                    {
                        "key": "experiment_hash",
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

    return yaml.dump(config_dict), config_hash, selected_policies#retorna o arquivo yaml de configuração do coletor, o valor de hash para essa configuração, e as políticas selecionadas
#######################################################################################################################################
#Cria e substitui o configmap collector-config com a nova configuração
def update_configmap(config_yaml):
    cm_body = client.V1ConfigMap(#Cria o novo config map a partir do arquivo yaml gerado anteriormente a partir das novas políticas
        metadata=client.V1ObjectMeta(name=CONFIGMAP_NAME, namespace=NAMESPACE),
        data={"config.yaml": config_yaml}
    )
    try:#Tenta substituir um configmap já criado anteriormente
        core_v1.replace_namespaced_config_map(CONFIGMAP_NAME, NAMESPACE, cm_body)
        print(f"ConfigMap {CONFIGMAP_NAME} updated")
    except client.exceptions.ApiException as e:#Se não existia nenhum configmap, então cria um novo com a nova configuração
        if e.status == 404:
            core_v1.create_namespaced_config_map(NAMESPACE, cm_body)
            print(f"ConfigMap {CONFIGMAP_NAME} created")
        else:
            raise
#######################################################################################################################################
#Atualiza o deployment collector, adicionado o config-hash como annotation no pod. Isso força o kubernetes a verificar que o template mudou, e gera um rolling update automático que substitui os pods com a configuração nova
def rolling_update_deployment(config_yaml, config_hash):
    patch = {#Patch a ser aplicado no pod
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
    apps_v1.patch_namespaced_deployment(#Aplicação do patch com a hash gerada para a nova configuração
        name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=patch
    )
    print(f"Deployment {DEPLOYMENT_NAME} patched with config hash {config_hash}")

#######################################################################################################################################
#Função que fica esperando para ver se o rollout está completo e o agente pode seguir com suas atividades
def wait_for_rollout_ready():
    while True:
        deployment = apps_v1.read_namespaced_deployment(DEPLOYMENT_NAME, NAMESPACE)#Busca o objeto que representa o deploy do coletor no namespace especificado
        desired = deployment.spec.replicas#Verifica quantos pods estão especificados para se ter do collector, no caso apenas 1
        available = deployment.status.available_replicas or 0 #Verifica quantas réplicas estão disponíveis atualmente dentro dos deployments
        if available >= desired:#Se o número de réplicas for maior ou igual o desejado, considera-se o rollout completo e sai do loop
            print("Rollout completo!")
            return
        print(f"Aguardando rollout... {available}/{desired} prontos")#Se ainda continua com menos que o número desejado de pods, aguarda 2 segundos até tentar novamente
        time.sleep(2)
#######################################################################################################################################
#Função principal
if __name__ == "__main__":
    first = True

    while True:
        if first:#Primeira hash não é utilizada e nem gera traces
            old_hash = "jausj"
            first = False
        else:
            old_hash = config_hash
        config_yaml, config_hash, selected_policies = generate_config()#Gera o yaml do novo collector-config, a hash e as políticas selecionadas

        update_configmap(config_yaml)#Atualiza o configmap dentro do cluster

        rolling_update_deployment(config_yaml, config_hash)#faz o rolling update para que o kubernetes troque o antigo coletor por um novo com a nova configuração

        print("Waiting for new pod to be ready...")
        wait_for_rollout_ready()#espera todo o rollout estar completo
        print("New pod ready!")

        save_history(config_hash, selected_policies)#salva a hash criada assim como o arquivo com as políticas selecionadas em um arquivo para futura análise
        entropia = export_traces_by_hash(old_hash)#calcula a entropia 
        print(f"Entropia dos traces: {entropia}")

        time.sleep(60)
