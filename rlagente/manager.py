import time
import hashlib
from kubernetes import client, config
import json
import random
import yaml
import os
from history import *
from es_utils import *

from agent import ReinforceAgent



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
def generate_config(selected_policies, config_hash):
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
                "decision_wait": "40s",
                "num_traces": 15000,
                "expected_new_traces_per_sec": 1000,
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

    return yaml.dump(config_dict)#retorna o arquivo yaml de configuração do coletor, o valor de hash para essa configuração, e as políticas selecionadas
#######################################################################################################################################
#Cria e substitui o configmap collector-config com a nova configuração
def update_configmap(config_yaml):
    cm_body = client.V1ConfigMap(#Cria o novo config map a partir do arquivo yaml gerado anteriormente a partir das novas políticas
        metadata=client.V1ObjectMeta(name=CONFIGMAP_NAME, namespace=NAMESPACE),
        data={"config.yaml": config_yaml}
    )
    try:#Tenta substituir um configmap já criado anteriormente
        core_v1.replace_namespaced_config_map(CONFIGMAP_NAME, NAMESPACE, cm_body)
        #print(f"ConfigMap {CONFIGMAP_NAME} updated")
    except client.exceptions.ApiException as e:#Se não existia nenhum configmap, então cria um novo com a nova configuração
        if e.status == 404:
            core_v1.create_namespaced_config_map(NAMESPACE, cm_body)
            #print(f"ConfigMap {CONFIGMAP_NAME} created")
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
    #print(f"Deployment {DEPLOYMENT_NAME} patched with config hash {config_hash}")

#######################################################################################################################################
#Função que fica esperando para ver se o rollout está completo e o agente pode seguir com suas atividades
def wait_for_rollout_ready():
    while True:
        deployment = apps_v1.read_namespaced_deployment(DEPLOYMENT_NAME, NAMESPACE)#Busca o objeto que representa o deploy do coletor no namespace especificado
        desired = deployment.spec.replicas#Verifica quantos pods estão especificados para se ter do collector, no caso apenas 1
        available = deployment.status.available_replicas or 0 #Verifica quantas réplicas estão disponíveis atualmente dentro dos deployments
        if available >= desired:#Se o número de réplicas for maior ou igual o desejado, considera-se o rollout completo e sai do loop
            #print("Rollout completo!")
            return
        #print(f"Aguardando rollout... {available}/{desired} prontos")#Se ainda continua com menos que o número desejado de pods, aguarda 2 segundos até tentar novamente
        time.sleep(2)
#######################################################################################################################################
def trace_penalty_function(traces, C, k=25, midpoint=0.20):
    x = traces / C
    return 1 / (1 + math.exp(-k * (x - midpoint)))

    
#Função de reward para o conjunto de regras definido
def reward_function(entropy, traces, alpha=1.0, beta=1.0, C = 10000, lambd=3.0):
    norm_entropy = entropy/10

    trace_penalty = trace_penalty_function(traces, C)

    return alpha * norm_entropy - beta * trace_penalty
#######################################################################################################################################
#Função principal
if __name__ == "__main__":

    MAX_NUMBER_EPISODES = 300
    current_episode = 0

    current_test = 0
    MAX_NUMBER_OF_TESTS = 25
    history_buffer = []

    with open(POLICIES_FILE, "r") as f:
        all_policies = json.load(f)

    agent = ReinforceAgent(num_policies = len(all_policies))
    
    first = True

    while True:
        current_episode = current_episode + 1
        if first:#Primeira hash não é utilizada e nem gera traces
            old_hash = "jausj"
            first = False
        else:
            old_hash = config_hash
    
        selected_policies, selected_actions = agent.select_actions(all_policies)
        
        policies_str = json.dumps(selected_policies, sort_keys = True)
        timestamp = str(time.time())
        hash_input = policies_str + timestamp
        config_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8] 
        config_yaml = generate_config(selected_policies, config_hash)

        update_configmap(config_yaml)
        rolling_update_deployment(config_yaml, config_hash)

        wait_for_rollout_ready()

        entropia, number_of_traces = export_traces_by_hash(old_hash)

        reward = reward_function(entropia, number_of_traces)
        agent.update(selected_policies, reward, selected_actions)
        print(f"Hash: {config_hash}, reward: {reward}, Entropia: {entropia}, Número de traces: {number_of_traces}")

        history_buffer.append({
            "episode": current_episode,
            "hash": old_hash,
            "entropy": entropia,
            "reward": reward,
            "number_of_traces": number_of_traces,
        })

        if current_episode < MAX_NUMBER_EPISODES:
            time.sleep(60)
        else:
            with open("episodes_history_" + str(current_test) + ".json", "w") as f:
                json.dump(history_buffer, f, indent=2)
            agent.save_policies(current_test)
            first = True
            agent = ReinforceAgent(num_policies = len(all_policies))
            current_test = current_test + 1
            history_buffer = []
            current_episode = 0
            if current_test >= MAX_NUMBER_OF_TESTS:
                time.sleep(100000)




    #     config_yaml, config_hash, selected_policies = generate_config()#Gera o yaml do novo collector-config, a hash e as políticas selecionadas

    #     update_configmap(config_yaml)#Atualiza o configmap dentro do cluster

    #     rolling_update_deployment(config_yaml, config_hash)#faz o rolling update para que o kubernetes troque o antigo coletor por um novo com a nova configuração

    #     #print("Waiting for new pod to be ready...")
    #     wait_for_rollout_ready()#espera todo o rollout estar completo
    #     #print("New pod ready!")

    #     save_history(config_hash, selected_policies)#salva a hash criada assim como o arquivo com as políticas selecionadas em um arquivo para futura análise
    #     entropia = export_traces_by_hash(old_hash)#calcula a entropia 
    #     #print(f"Entropia dos traces: {entropia}")

    #     time.sleep(60)
