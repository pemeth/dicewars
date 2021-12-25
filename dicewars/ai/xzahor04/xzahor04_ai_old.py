import logging
import time
from pprint import pprint
from random import random

from dicewars.client.ai_driver import BattleCommand, EndTurnCommand, TransferCommand
from dicewars.ai.utils import possible_attacks as pa

from dicewars.client.game.board import Board

class AI:
    def __init__(self, player_name, board, players_order, max_transfers):
        self.player_name = player_name
        self.logger = logging.getLogger('AI')

        self.stage = 'attack'   # ATTACK | DEFEND | TRANSFER
        self.MIN_DICE_DIFF = 3
        self.MAX_TRANSFERS = max_transfers

        # Get player color for debugging
        print(self.player_color(self.player_name))

        self.next_move = None


    def ai_turn(self, board, nb_moves_this_turn, nb_transfers_this_turn, nb_turns_this_game, time_left):
        """AI agent's turn
        """

        # Helper move
        if self.next_move is not None:
            tmp = self.next_move
            self.next_move = None
            print("HELPER MOVE")
            print(tmp)
            print()
            return TransferCommand(tmp[1][0], tmp[0][0])

        # Get possible attacks when none are defined
        possible_attacks = self.get_attacks(board)
        pprint(possible_attacks)

        # Loop from last state and search for possible attacks
        for i in range(len(possible_attacks)):
            # Get attack
            attack = possible_attacks[i]

            generated_attack = self.get_attack(board, attack[0], attack[1], attack[2], (6 - nb_transfers_this_turn))

            # Attack is not possible
            if generated_attack is None or len(generated_attack) == 0:
                continue
            
            # We got multiple values, attack with second deffense
            if isinstance(generated_attack, list):
                self.next_move = generated_attack[1]
                generated_attack = generated_attack[0]
            
            print("POSSIBLE ATTACK")
            print(generated_attack)
            print()
            time.sleep(1)
            return BattleCommand(generated_attack[0][0], generated_attack[1][0])

        print("NO move found ending")
        print("Continue ? ")
        input("Continue ? ")

        return EndTurnCommand()

    def get_attack(self, board, attacker, deffenders, helpers, transfers_left):
        alls_are_1 = True
        max_dice_danger = 1
        possible_attack = None

        # Enemies are sorted (HIGHER > LOWER), first we found is good
        for deffender in deffenders:
            # Possible attack is selected
            if not possible_attack is None:
                # Loop through all deffenders and when all others are 1
                if deffender[1] > max_dice_danger:
                    alls_are_1 = False
                    max_dice_danger = deffender[1]
                    break

                continue

            # Calculate probability
            prob = self.attack_succcess_probability(attacker[1], deffender[1])
            
            # Attack only when 50% chance is, or when 45% and higher attack 1/2 
            if prob > 0.5 or (prob > 0.45 and random() > 0.5):

                # Check possible future that can happen, when it is okay set possible attack
                if self.check_possible_enemy_moves(board, attacker, deffender):
                    possible_attack = (attacker, deffender)
                continue
            # Difference is higher, so we would loose
            else:
                alls_are_1 = False
                continue
        
        # No attack found
        if possible_attack is None:
            print("ERR\tNo attack found")
            return None

        # Attack without any danger found
        if alls_are_1:
            return possible_attack
        
        # No more transfers
        if transfers_left == 0:
            print("ERR\tNo more transfers")
            return None

        print("MAX DICE DANGER ", max_dice_danger)

        # Attack with possible danger Try to find helper that can aid us
        for helper in helpers:
            if max_dice_danger <= helper[1]:
                return [possible_attack, ((attacker[0], 1), helper)]

        # No move found
        print("ERR\tNo move found")
        return None

    def check_possible_enemy_moves(self, board, attacker, deffender):
        # Get deffender area
        deff_area = board.get_area(deffender[1])
        
        # Get our area around deffender
        neighbours = [board.get_area(neigh) for neigh in deff_area.get_adjacent_areas_names()]
        
        # Get all helpers except area with which we are attacking
        helpers = [helper for helper in neighbours if helper.get_owner_name() == self.player_name and helper.get_name() != attacker[0]]
        
        # Get all possible attacks that could endanger us in the future
        enemies = [enemy for enemy in neighbours if enemy.get_owner_name() != self.player_name and enemy.get_dice() > attacker[1]]
        
        # Danger, do not make move
        if len(enemies) > 0:
            return False

        # Movep possible
        return True


    def calc_score(self, att_dice, deff_dice):
        # Calculte probability of win
        prob = self.attack_succcess_probability(att_dice, deff_dice)

        # Winner when >= 0.6 or 8 dices have both
        if prob >= 0.7 or (att_dice == deff_dice and att_dice == 8):
            print('W:\t', prob , '\t', deff_dice, '\t', deff_dice * prob)
            return deff_dice

        # Loss
        print('L:\t',prob , '\t', ((att_dice // 4) - (att_dice - 1)), '\t', ((att_dice // 4) - (att_dice - 1)) * (1 - prob))
        return ((att_dice // 4) - (att_dice - 1))

    """
        Return all possible attacks sorted
        by score
    """
    def get_attacks(self, board):
        # Get all areas that border with enemy
        border_areas = board.get_player_border(self.player_name)
        unborder_areas = [area for area in board.get_player_areas(self.player_name) if area not in border_areas]

        """"
            Will consist of array of tuples
            tuple: (attacker=(id, dice_count), [sorted array of possible enemies (id, dice_count)])
        """
        attacks = []

        for border_area in border_areas:
            # Get all areas around our area
            neighboars = border_area.get_adjacent_areas_names()
            helpers = []
            enemies = []

            for neighboar in neighboars:
                neigh_area = board.get_area(neighboar)
                
                # Add our areas as helpers
                if neigh_area.get_owner_name() == self.player_name:
                    # Append helper when we can help
                    if neigh_area.can_attack() and neigh_area in unborder_areas:
                        helpers.append((neigh_area.get_name(), neigh_area.get_dice()))
                    continue
                
                # Append enemies
                enemies.append((neigh_area.get_name(), neigh_area.get_dice()))
            
            # Skip area when we cannot attack and we got no helpers
            if not border_area.can_attack() and len(helpers) == 0:
                continue

            # Sort enemies by dice count
            enemies = sorted(enemies, reverse=True, key=lambda enemy: enemy[1])

            attacks.append(((border_area.get_name(), border_area.get_dice()), enemies, helpers))
        
        # Return attacks
        return attacks


    def player_color(self, player_name):
        """Return color of a player given his name
        """
        return {
            1: 'Green',
            2: 'Blue',
            3: 'Red',
            4: 'Yellow',
            5: 'Light blue',
            6: 'Purple',
            7: 'White',
            8: 'Light purple'
        }[player_name]

    def attack_succcess_probability(self, atk, df):
        """Dictionary with pre-calculated probabilities for each combination of dice

        Parameters
        ----------
        atk : int
            Number of dice the attacker has
        df : int
            Number of dice the defender has

        Returns
        -------
        float
        """
        print(atk, df, '\n')
        return {
            2: {
                1: 0.83796296,
                2: 0.44367284,
                3: 0.15200617,
                4: 0.03587963,
                5: 0.00610497,
                6: 0.00076625,
                7: 0.00007095,
                8: 0.00000473,
            },
            3: {
                1: 0.97299383,
                2: 0.77854938,
                3: 0.45357510,
                4: 0.19170096,
                5: 0.06071269,
                6: 0.01487860,
                7: 0.00288998,
                8: 0.00045192,
            },
            4: {
                1: 0.99729938,
                2: 0.93923611,
                3: 0.74283050,
                4: 0.45952825,
                5: 0.22044235,
                6: 0.08342284,
                7: 0.02544975,
                8: 0.00637948,
            },
            5: {
                1: 0.99984997,
                2: 0.98794010,
                3: 0.90934714,
                4: 0.71807842,
                5: 0.46365360,
                6: 0.24244910,
                7: 0.10362599,
                8: 0.03674187,
            },
            6: {
                1: 0.99999643,
                2: 0.99821685,
                3: 0.97529981,
                4: 0.88395347,
                5: 0.69961639,
                6: 0.46673060,
                7: 0.25998382,
                8: 0.12150697,
            },
            7: {
                1: 1.00000000,
                2: 0.99980134,
                3: 0.99466336,
                4: 0.96153588,
                5: 0.86237652,
                6: 0.68516499,
                7: 0.46913917,
                8: 0.27437553,
            },
            8: {
                1: 1.00000000,
                2: 0.99998345,
                3: 0.99906917,
                4: 0.98953404,
                5: 0.94773146,
                6: 0.84387382,
                7: 0.67345564,
                8: 0.47109073,
            },
        }[atk][df]
