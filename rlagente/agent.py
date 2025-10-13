import numpy as np 
import json
import os

class ReinforceAgent:
    def __init__(self,num_policies, lr=0.2, baseline_decay = 0.9, policies_path='policy_probabilities.json'):
        self.num_policies = num_policies
        self.policies_path = policies_path

        with open(self.policies_path, 'r') as f:
            self.probs = np.array(json.load(f))

        self.lr = lr
        self.baseline = 0.0
        self.baseline_decay = baseline_decay

    
    def select_actions(self, all_policies):
        actions = []
        selected = []

        for i, policy in enumerate(all_policies):
            if np.random.rand() < self.probs[i]:
                selected.append(policy)
                actions.append(1)
            else:
                actions.append(0)
        
        if not selected:
            idx = np.random.randint(len(all_policies))
            selected = [all_policies[idx]]
            actions[idx] = 1
        
        self.last_actions = np.array(actions)
        return selected

    def update(self, selected_policies, reward):
        self.baseline = (self.baseline_decay * self.baseline +(1-self.baseline_decay)*reward)

        advantage = reward - self.baseline

        grad = self.last_actions - self.probs
        self.probs += self.lr * advantage * grad
        self.probs = np.clip(self.probs, 0.01, 0.99)

    def save_policies(self):
        with open(self.policies_path, "w") as f:
            json.dump(self.probs.tolist(), f)


    def save_history(self, reward, number_of_traces, path="historico.json"):
        historico = []

        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    content = f.read().strip()
                    if content:  # só tenta decodificar se tiver algo
                        historico = json.loads(content)
                except json.JSONDecodeError:
                    historico = []  # arquivo corrompido ou inválido

        historico.append({
            "reward": reward,
            "number_of_traces": number_of_traces,
        })

        with open(path, "w") as f:
            json.dump(historico, f, indent=2)

        



    
        