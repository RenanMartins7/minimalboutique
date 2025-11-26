import json
import matplotlib.pyplot as plt

# Configurações
NUM_RUNS = 5
FILE_PATTERN = "episodes_history_{}.json"

# ---- 1. Ler todos os arquivos e guardar recompensas/episódios ----
all_rewards = []
all_episodes = []

for i in range(NUM_RUNS):
    file_name = FILE_PATTERN.format(i)
    with open(file_name, "r") as f:
        data = json.load(f)

    rewards = [entry["reward"] for entry in data]
    episodes = [entry["episode"] for entry in data]

    all_rewards.append(rewards)
    all_episodes.append(episodes)

# Opcional: garantir que todas as execuções tenham o mesmo número de episódios
# Usando o mínimo tamanho para evitar IndexError
min_len = min(len(r) for r in all_rewards)
all_rewards = [r[:min_len] for r in all_rewards]
all_episodes = [e[:min_len] for e in all_episodes]

# Vamos usar os episódios da primeira execução como referência
episodes = all_episodes[0]

# ---- 2. Calcular a média de recompensa por episódio ----
mean_rewards = []
for t in range(min_len):
    mean_t = sum(run_rewards[t] for run_rewards in all_rewards) / NUM_RUNS
    mean_rewards.append(mean_t)

# ---- 3. Gráfico da MÉDIA de recompensa por episódio ----
plt.figure(figsize=(12, 5))
plt.plot(episodes, mean_rewards, marker='o')
plt.title("Recompensa Média por Episódio (5 execuções)")
plt.xlabel("Episódio")
plt.ylabel("Recompensa Média")
plt.grid(True)
plt.tight_layout()
plt.show()

# ---- 4. Gráfico com TODAS AS CURVAS individuais ----
plt.figure(figsize=(12, 5))
for i, rewards in enumerate(all_rewards):
    plt.plot(episodes, rewards, marker='o', label=f"Execução {i+1}")

plt.title("Recompensa por Episódio em Cada Execução")
plt.xlabel("Episódio")
plt.ylabel("Recompensa")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

