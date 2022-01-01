import logging
import numpy as np
import torch
import random
import copy
from collections import deque
from dicewars.client.ai_driver import BattleCommand, EndTurnCommand
from dicewars.ai.utils import possible_attacks
from dicewars.ai.xzahor04.model import Linear_QNet, QTrainer

MAX_MEMORY = 100000
BATCH_SIZE = 1000

class AI:
    def __init__(self, player_name, board, players_order, max_transfers):
        self.player_name = player_name
        self.logger = logging.getLogger('AI')

        colors = {
            1: 'Green',
            2: 'Blue',
            3: 'Red',
            4: 'Yellow',
            5: 'Light blue',
            6: 'Purple',
            7: 'White',
            8: 'Light purple'
        }

        print(colors[player_name])

        self.states_old = []
        self.num_actions = 0

        #self.moves = 0
        #self.epsilon = 0 # randomness
        self.memory = deque(maxlen=MAX_MEMORY) # popleft()
        self.model = Linear_QNet(7, 256, 2)
        self.model.load()
        self.trainer = QTrainer(self.model, lr=0.001, gamma=0.9)

    def __del__(self):

        #print("Executing long train with all acquired data and saving model to file.")
        # TODO spytat sa, ci toto je nutne spravit este aj tu (okrem kazdeho jednotlive kola) - lebo sa to takmer nikdy nedokonci v tejto metode?
        #self.train_long_memory()

        self.model.save()

    def ai_turn(self, board, nb_moves_this_turn, nb_transfers_this_turn, nb_turns_this_game, time_left):

        self.train(board)

        # get areas that we can attack from
        attacks = possible_attacks(board, self.player_name)

        for source, target in attacks:

            new_board = copy.deepcopy(board)

            new_source = new_board.get_area(source.get_name())
            new_target = new_board.get_area(target.get_name())

            # assume the attack is successful, simulate the changes
            new_target.set_owner(new_source.get_owner_name())
            new_target.set_dice(new_source.get_dice() - 1)
            new_source.set_dice(1)

            # current game state
            state_old, areas_names = self.get_state(new_board, new_target)

            # get move
            final_move = self.get_action(state_old)
            self.num_actions += 1

            self.states_old.append((state_old, areas_names, final_move))

            print("Added Old State: ", state_old, "Areas: ", areas_names)
            print("Final move ", final_move)

            # perform the move
            if(final_move[0] == 1):
                return BattleCommand(source.get_name(), target.get_name())

        self.num_actions = 0
        return EndTurnCommand()

    def train(self, board):
        # Check the state of the game after our moves
        if (self.states_old != [] and self.num_actions == 0):

            for (state_old, areas_names, final_move) in self.states_old:

                #attack_area = board.get_area(areas_names[0])
                defend_area = board.get_area(areas_names[0])

                # get state after attack
                state_new, new_areas_names = self.get_state(board, defend_area)

                #print("Added New State: ", state_new, "Areas: ", new_areas_names)

                    # set rewards based on the new state vs old state
                reward = self.get_reward(state_old, state_new, final_move)

                #print("Old State: ", state_old, " New State: ", state_new, " Reward: ", reward, " Final move: ", final_move)

                # train short memory
                #self.train_short_memory(state_old, final_move, reward, state_new, False)

                # save to memory
                self.remember(state_old, final_move, reward, state_new, False)


            self.train_long_memory()

            # clear the arrays
            self.states_old = []

    def get_reward(self, old_state, new_state, final_move):
        reward = 0

        # NN said can hold the area after attack
        if(final_move[0] == 1):
            # but in the end we lost it
            if(new_state[6] == 0):
                reward -= old_state[1] - old_state[0]
            else: # We kept it, success
                reward += old_state[0] - old_state[1]

        else: # NN said we can not hold the area
            # but we held it anyway
            if(new_state[6] == 1):
                reward -= old_state[0] - old_state[1]
            else: # We did not hold it, correct prediction means positive reward
                reward += old_state[1] - old_state[0]

        return reward

    def get_state(self, board, defender_area):

        defender_area_dice = defender_area.get_dice()

        defender_area_adj_areas_names = defender_area.get_adjacent_areas_names()

        their_areas_names = [area_name for area_name in defender_area_adj_areas_names if board.get_area(area_name).get_owner_name() != self.player_name]

        # Get all dice count of these areas
        their_areas_names_dice = []
        for area_name in their_areas_names:
            their_areas_names_dice.append(board.get_area(area_name).get_dice())

        their_areas_names_dice = sorted(their_areas_names_dice, reverse=True)

        # Take at most 5 strongest dice
        their_areas_names_dice = their_areas_names_dice[:5]

        state = []

        state.append(defender_area_dice)

        for their_area_name_dice in their_areas_names_dice:
            state.append(their_area_name_dice)

        for i in range(5 - len(their_areas_names_dice)):
            state.append(0)

        if(defender_area.get_owner_name() == self.player_name):
            state.append(1)
        else:
            state.append(0)


        areas_names = []

        areas_names.append(defender_area.get_name())

        return np.array(state, dtype=int), areas_names

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done)) # popleft if MAX_MEMORY is reached

    def train_long_memory(self):
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE) # list of tuples
        else:
            mini_sample = self.memory

        if(not mini_sample):
            return

        states, actions, rewards, next_states, dones = zip(*mini_sample)

        self.trainer.train_step(states, actions, rewards, next_states, dones)

    def train_short_memory(self, state, action, reward, next_state, done):
        self.trainer.train_step(state, action, reward, next_state, done)

    def get_action(self, state):
        final_move = [0,0]

        state0 = torch.tensor(state, dtype=torch.float)
        prediction = self.model(state0)
        move = torch.argmax(prediction).item()
        final_move[move] = 1

        return final_move
