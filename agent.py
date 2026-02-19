import torch
import torch.optim as optim
import random
from model import DQN
from buffer import ReplayBuffer

class DQNAgent:
    def __init__(self):
        self.model = DQN(4, 4)
        self.target = DQN(4, 4)
        self.target.load_state_dict(self.model.state_dict())

        self.buffer = ReplayBuffer()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)

        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.05

    def act(self, state):
        if random.random() < self.epsilon:
            return random.randint(0, 3)
        with torch.no_grad():
            return self.model(torch.FloatTensor(state)).argmax().item()

    def remember(self, s, a, r, s2):
        self.buffer.add((s, a, r, s2))

    def train(self, batch_size=64):
        if len(self.buffer) < batch_size:
            return

        batch = self.buffer.sample(batch_size)
        states, actions, rewards, next_states = zip(*batch)

        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)

        q = self.model(states).gather(1, actions.unsqueeze(1)).squeeze()
        q_next = self.target(next_states).max(1)[0]
        target = rewards + self.gamma * q_next

        loss = torch.nn.MSELoss()(q, target.detach())
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        if self.epsilon > self.epsilon_min:
          self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def update_target(self):
        self.target.load_state_dict(self.model.state_dict())


