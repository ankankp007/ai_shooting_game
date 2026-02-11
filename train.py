from agent import DQNAgent
import random

EPISODES = 1000

player = DQNAgent()
enemy = DQNAgent()

for ep in range(EPISODES):
    px, ex = random.randint(0, 800), random.randint(0, 800)
    p_health, e_health = 100, 100

    for step in range(200):
        state = [px/800, ex/800, p_health/100, e_health/100]

        pa = player.act(state)
        ea = enemy.act(state)

        reward_p = -0.01
        reward_e = -0.01

        if pa == 2 and abs(px - ex) < 40:
            reward_p += 10
            reward_e -= 10
            e_health -= 10

        if ea == 2 and abs(ex - px) < 40:
            reward_e += 10
            reward_p -= 10
            p_health -= 10

        next_state = [px/800, ex/800, p_health/100, e_health/100]

        player.remember(state, pa, reward_p, next_state)
        enemy.remember(state, ea, reward_e, next_state)

        player.train()
        enemy.train()

    if ep % 20 == 0:
        player.update_target()
        enemy.update_target()
        print(f"Episode {ep} completed")

print("Training finished ")
