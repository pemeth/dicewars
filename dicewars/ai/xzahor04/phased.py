import logging
import time
from pprint import pprint
from random import random
from collections import deque

from dicewars.client.ai_driver import BattleCommand, EndTurnCommand, TransferCommand
from dicewars.client.game.board import Board

class AI:
    def __init__(self, player_name, board, players_order, max_transfers):
        self.player_name = player_name
        self.logger = logging.getLogger('AI')

        self.stage = 'attack' # attack | deffend | transfer
        self.MAX_TRANSFERS = max_transfers

        # Print player color for debuging
        AI_Debug.print_color(player_name)
        
        self.attack_helper_attack_moves = []
        self.attack_helper_deffense_moves = []
        self.transfer_moves = []
        self.deffend_moves = []

        self.attack_move = None


    def ai_turn(self, board, nb_moves_this_turn, nb_transfers_this_turn, nb_turns_this_game, time_left):
        """AI agent's turn
        """

        # When there are deffend moves, do them
        if len(self.deffend_moves) > 0:
            move = self.deffend_moves.pop()
            return TransferCommand(move[0], move[1])



        # When there are attack_helper_attack_moves moves, do them before attack
        if len(self.attack_helper_attack_moves) > 0:
            # Pop one out, and do move
            move = self.attack_helper_attack_moves.pop()
            return TransferCommand(move[0], move[1])

        # Do attack move after attack helper moves all helpers to increase attack
        if self.attack_move is not None:
            tmp_attack_move = self.attack_move
            self.attack_move = None
            return BattleCommand(tmp_attack_move[0], tmp_attack_move[1])

        # When there are attack_helper_deffense_moves, do them after attack
        if len(self.attack_helper_deffense_moves) > 0:
            # Pop one out, and do move
            move = self.attack_helper_deffense_moves.pop()
            return TransferCommand(move[0], move[1])

        # Attacking stage
        if self.stage == 'attack':
            # Generate attack moves, with maximum of 3 helping transfers
            attack = self.get_attack(board, (3 - nb_moves_this_turn))
            
            # When after attack there are attack_helper_moves, do them first
            if len(self.attack_helper_attack_moves) > 0:
                self.attack_move = attack
                # Pop one out, and do move
                move = self.attack_helper_attack_moves.pop()
                return TransferCommand(move[0], move[1])

            AI_Debug.print_attack(board, attack)

            # When we possible attack, do it
            if attack is not None:
                return BattleCommand(attack[0], attack[1])

            # No attack found, change to deffend
            self.stage = 'deffend'

        if self.stage == 'deffend':
            # Generate deffense moves, with maximum of 3 helping transfers
            self.deffend_moves = self.gen_deffense_moves(board, (6 - nb_transfers_this_turn))

            # When there are defined deffend moves, go through them
            if len(self.deffend_moves) > 0:
                move = self.deffend_moves.pop()
                return TransferCommand(move[0], move[1])

            # No more deffender moves, go to transfer stage
            self.stage = 'transfer'
        
        if self.stage == 'transfer':
            print('Transfers left', 6 - nb_transfers_this_turn)

            # When there are defined transfer moves, go through them
            if len(self.transfer_moves):
                move = self.transfer_moves.pop()
                return TransferCommand(move[0], move[1])

            # Generate transfer moves, with whats left after attack and deffend
            self.transfer_moves = self.gen_transfer_moves(board, (6 - nb_transfers_this_turn))

            # No more moves
            if len(self.transfer_moves) == 0:
                self.stage = 'attack'
                return EndTurnCommand()

        return EndTurnCommand()

    def get_possible_attacks(self, board):
        """Function to generate combination of attack deffenders and helpers
       
        Parameters
        ----------
        board : Board

        Returns
        -------
        array<
            Tuple<(
                (ATTACKER_ID, ATTACKER_DICE),
                array<Tuple(DEFFENDER_ID, DEFFENDER_DICE)>
                array<Tuple(HELPER_ID, HELPER_DICE)>
            )
        >

        """
        # Get all areas we border with enemies that can attack
        our_border_areas = [area for area in board.get_player_border(self.player_name) if area.can_attack()]
        
        possible_attacks = []

        # Generate for each area, enemies
        for our_border_area in our_border_areas:
            deffenders = []
            helpers = []

            for deffender_id in our_border_area.get_adjacent_areas_names():
                # Skip area that is our attacker
                if our_border_area.get_name() == deffender_id:
                    continue

                # Get deffender area
                deffender_area = board.get_area(deffender_id)

                # It is ours, add to helpers
                if deffender_area.get_owner_name() == self.player_name:
                    # Helper can only be the one that have more than 1 cube and are not endangered by enemy
                    if deffender_area.get_dice() != 1 and not deffender_area in our_border_areas:
                        helpers.append((deffender_area.get_name(), deffender_area.get_dice()))

                # It is enemy, add to defenders
                else:
                    deffenders.append((deffender_area.get_name(), deffender_area.get_dice()))

            # After that sort out deffender and helpers based on their dice count
            deffenders = sorted(deffenders, reverse=True, key=lambda deffender: deffender[1])
            helpers = sorted(helpers, reverse=True, key=lambda helper: helper[1])

            # Append to possible attack when there 
            possible_attacks.append(
                (
                    (our_border_area.get_name(), our_border_area.get_dice()),
                    deffenders,
                    helpers
                )
            )
        
        # Before returning sort out based attack dice count
        return sorted(possible_attacks, reverse=True, key=lambda attacker: attacker[0][1])

    def get_possible_endandered_areas(self, board):
         # Get all areas we border with enemies
        our_border_areas = [area for area in board.get_player_border(self.player_name)]

        endangered_areas = []
        
        # Loop through areas and find endangered ones
        for area in our_border_areas:
            # Skip areas with 8 dices
            if area.get_dice() == 8:
                continue

            # Get neigbours
            possible_enemy_ids = area.get_adjacent_areas_names()

            helpers = []
            enemies = []

            for possible_enemy_id in possible_enemy_ids:
                possible_enemy_area = board.get_area(possible_enemy_id)

                # Add enemy area to enemies
                if possible_enemy_area.get_owner_name() != self.player_name:

                    # Add enemy when there is chance to loose
                    if possible_enemy_area.get_dice() > 1 and AI_Utils.attack_win_loss(possible_enemy_area.get_dice(), area.get_dice()):
                        enemies.append((possible_enemy_area.get_name(), possible_enemy_area.get_dice()))

            # Skip when there are no enemies
            if len(enemies) == 0:
                continue

            # Sort enemies by dice count
            enemies = sorted(enemies, reverse=True, key=lambda enemy: enemy[1])
        
            endangered_areas.append(
                (
                    (area.get_name(), area.get_dice()),
                    enemies[0]
                ) 
            )

        # Sort by difference between ENEMY and our DICE count
        return sorted(endangered_areas, key=lambda endangered_area: endangered_area[0][1] - endangered_area[1][1])

    def gen_helping_defense_path(self, board, deffender, dice_count, ignore_areas, threat, transfers_left):
        if transfers_left <= 0:
            return []

        # 
        for helper in AI_Utils.get_helpers(board, deffender, ignore_areas, self.player_name):
            # Found helper that is able to help, generate move
            if helper[1] > 1 and ((dice_count + helper[1] - 1) - threat[1]) >= -1:
                return [(helper[0], deffender[0])]

            # Not found, try recursive search
            else:
                path = self.gen_helping_defense_path(
                    board,
                    helper,
                    (dice_count + helper[1] - 1),
                    ignore_areas + [helper[0]],
                    threat,
                    (transfers_left -  1)
                )

                # Path not found, continue
                if len(path) == 0:
                    continue

                # Path found, return
                return path + [(helper[0], deffender[0])]

        return []

    def gen_deffense_moves(self, board, transfers_left):
        # Get endangered areas
        endangered_areas = self.get_possible_endandered_areas(board)

        # Go through each endangered area, and find helping path
        for endangered_area in endangered_areas:
            # Find path
            path = self.gen_helping_defense_path(board, endangered_area[0], endangered_area[0][1], [endangered_area[0]], endangered_area[1], transfers_left)
            
            # Path not found, go to another area
            if len(path) == 0:
                continue

            # Reverse path so we can pop it out
            path.reverse()

            # Return found path
            return path

        return []

    def gen_transfer_moves(self, board, transfers_left):
        # No more transfers left, end
        if transfers_left == 0:
            return []
        
        # Get all endangered areas
        endangered_areas = self.get_possible_endandered_areas(board)

        # Try to move dices closer 


        return []

    """-----------------------------------------------------------------------------------------
                                        ATTACK
    -----------------------------------------------------------------------------------------"""
    def get_attack(self, board, transfers_left):

        def recursively_find_helping_attack_path(attacker_dice, deffender_dice, last_helper, helpers_used, transfers_left):
            print("NO helping attack path")
            return []

        def find_helping_path(deffender, helper_area, helpers_found, transfers_left):
            print("NO helping deffense path")
            return []

        def gen_helping_attack_path(board, attacker, dice_count, ignore_areas, deffender, transfers_left):
            # No transfers left
            if transfers_left <= 0:
                return []

            # Get all helpers
            for helper in AI_Utils.get_helpers(board, attacker, ignore_areas, self.player_name):
                # Clamp attack dice with highest 8 dice count
                attack_dice = AI_Utils.clamp_number_of_dices((dice_count + helper[1] - 1))
                
                # Last one needs to be higher than 1, and the probability of win needs to be True
                if helper[1] > 1 and AI_Utils.attack_win_loss(attack_dice, deffender[1]):
                    return [(helper[0], deffender[0])]
                # Not found, try recursive search
                else:
                    path = gen_helping_attack_path(
                        board,
                        helper,
                        (dice_count + helper[1] - 1),
                        ignore_areas + [helper[0]],
                        deffender,
                        (transfers_left -  1)
                    )

                    # Path not found, continue
                    if len(path) == 0:
                        continue

                    # Path found, return
                    return path + [(helper[0], deffender[0])]

            return []

        def find_helping_attack_path(attack, transfers_left):
            # There are no helpers, attack is not possible
            if len(attack[2]) == 0:
                return False

            # Calculate uplated value of attack with max value of 8
            updated_attack = AI_Utils.clamp_number_of_dices(attack[2][0][1] + attack[0][1])

            # Try the first helper, when he is able to help, return new move
            if AI_Utils.attack_win_loss(updated_attack, attack[1][0][1]):

                # When there is no future threat, do the move
                if not future_threats((attack[0][0],updated_attack), attack[1][0]):
                    self.attack_helper_attack_moves = [(attack[2][0][0], attack[0][0])]
                    return True

                # There is future threat, check for helping path after attack
                if find_helping_path_after_attack(attack, (transfers_left - 1)):
                    self.attack_helper_attack_moves = [(attack[2][0][0], attack[0][0])]
                    return True

            return []

            # Generate helping attack path
            attack_path = gen_helping_attack_path(
                board,
                attack[0],
                attack[0][1],
                [attack[0][0]],
                attack[1][0],
                transfers_left
            )

            # Path not found
            if len(attack_path) == 0:
                return False

            print("ATTACK PATH:")
            AI_Debug.print_attack(board, (attack[0][0], attack[1][0][0]))

            for a in attack_path:
                AI_Debug.print_move(board, a)

            # Path found, set and return True
            self.attack_helper_attack_moves = attack_path
            return False

        def find_helping_path_for_future_threat(attack, transfers_left):
            return False

        def find_helping_path_after_attack(attack, transfers_left):
            # We can attack, no helping path needed
            if len(attack[1]) <= 1:
                return True

            helpers = self.gen_helping_defense_path(board, (attack[0][0], 1), 1, [attack[0][0]], attack[1][1], transfers_left)

            print(attack[0])
            if len(helpers) > 0:
                print("FOUND HELPING PATH AFTER ATTACK")
                pprint(helpers)
            else:
                print("No helping path found")
            return False

        def future_threats(attacker, deffender):
            # Attacker dice after attack
            attacker_dices = attacker[1] - 1

            # Get deffender area
            deffender_area = board.get_area(deffender[0])
            
            # Get all enemy areas
            for enemy_id in deffender_area.get_adjacent_areas_names():
                # Get area
                enemy_area = board.get_area(enemy_id)

                # Skip our areas
                if enemy_area.get_owner_name() == self.player_name:
                    continue

                # Skip enemies with 1 dice count
                if enemy_area.get_dice() == 1:
                    continue

                # When there is enemy, calculate chance of winning against us, when we would loose return True
                if (attacker_dices - enemy_area.get_dice()) < -1:
                    return True

            # No threats
            return False

        def do_we_keep_area_after_attack(attack, transfers_left):
            # No one to endander us
            if len(attack[1]) <= 1:
                return True

            # No more transfers left, check only deffenders
            if transfers_left == 0:
                return attack[1][1][1] == 1             # We got sorted array, check only the second one

            # There are possible transfers

            # When there are no helpers, we cant do anything
            if len(attack[2]) == 0:
                return attack[1][1][1] == 1             # We got sorted array, check only the second one
            
            # When there are only 1 in deffense, we can skip
            if attack[1][1][1] == 1:
                return True

            # We found helper that is able to help
            if AI_Utils.attack_win_loss(attack[1][1][1], attack[2][0][1]) == False:
                self.attack_helper_deffense_moves = [(attack[2][0][0], attack[0][0])]
                return True

            return False

            # We did not found helper that is able to help us in 1 move, so go look through others in area
            for helper in attack[2]:
                
                helpers = find_helping_path(attack[1][1], board.get_area(helper[0]), [], transfers_left)

                # No path found, go to other
                if len(helpers) == 0:
                    continue
                
                # Path found
                self.attack_helper_deffense_moves = helpers

                return True

            # Attack is not possible
            return False

        # Get all areas we border with enemies that can attack, and return the best move
        attacks = self.get_possible_attacks(board)

        # Print out possible attacks
        AI_Debug.print_possible_attacks(attacks)

        # Go through all possible attacks
        for attack in attacks:
            # Check if we are able to win first fight
            if AI_Utils.attack_win_loss(attack[0][1], attack[1][0][1]):
                # When we possibly win fight, check surrounding of deffending area, FUTURE ENEMY MOVES
                if future_threats(attack[0], attack[1][0]):
                    # Try to find helping attack path
                    if find_helping_path_for_future_threat(attack, transfers_left):
                        # Attack was found
                        return (attack[0][0], attack[1][0][0])

                    # Path not found
                    continue

                # Check if we will be able to keep our area after attack
                if do_we_keep_area_after_attack(attack, transfers_left):
                    # We can do this move, return move
                    return (attack[0][0], attack[1][0][0])

                # We are unable to keep our area, try to find another attack
                continue
            
            # We are unable to win, try to find helpers that can help us, if not attack is impossible
            else:
                print('Possible loss')
                AI_Debug.print_move(board, (attack[0][0], attack[1][0][0]))
                # Try to find helping attack path
                if find_helping_attack_path(attack, transfers_left):
                    print("Helping attack found")
                    # Attack was found
                    return (attack[0][0], attack[1][0][0])
                print("Helping attack not found")
        
        # No attack is possible
        return None


class AI_Utils:
    def get_helpers(board, area, ignore_areas, player_name):
        # Get possible helpers of area
        possible_helpers = board.get_area(area[0]).get_adjacent_areas_names()

        helpers = []

        # Generate helpers
        for possible_helper in possible_helpers:
            poss_helper_area = board.get_area(possible_helper)

            # Skip enemy
            if poss_helper_area.get_owner_name() != player_name:
                continue

            # Skip area that we want to ignore, to stop cicling
            if poss_helper_area.get_name() in ignore_areas:
                continue

            # When area border with enemy skip
            if AI_Utils.border_with_enemy(board, poss_helper_area, player_name):
                continue

            # Our helper
            helpers.append((poss_helper_area.get_name(), poss_helper_area.get_dice()))

        # Sort by size
        return sorted(helpers, reverse=True, key=lambda helper: helper[1])

    def clamp_number_of_dices(n):
        if n > 8:
            return 8
        else:
            return n

    def border_with_enemy(board, area, player_name):
        # Get all neigbour areas
        neighbours = area.get_adjacent_areas_names()
        
        # Check every area, and when one is 
        for neighbour in neighbours:
            neigh_area = board.get_area(neighbour)

            if neigh_area.get_owner_name() != player_name:
                return True
        
        return False

    def attack_win_loss(atk, df):
        # Get probability
        prob = AI_Utils.attack_succcess_probability(atk, df)

        # We take those, these are almost 100% successfull
        if prob >= 0.8 or atk == 8:
            return True

        # We take those in 80% of cases
        if prob >= 0.6:
            return random() >= 0.2

        # Otherwise there is 50/50 chance
        if prob >= 0.4:
            return random() >= 0.5


        return False

    def attack_succcess_probability(atk, df):
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

class AI_Debug:

    def print_possible_attacks(possible_attacks):
        for pa in possible_attacks:
            print('Attacker:', pa[0][1])
            print('Deffenders: ', end='')
            for d in pa[1]:
                print(d[1], ', ', end='')
            print()
            print('Helpers: ', end='')
            for h in pa[2]:
                print(h[1], ', ', end='')
            print()
            print()

    def print_move(board, move):
        if move:
            a = board.get_area(move[0])
            b = board.get_area(move[1])
            print('Move: ', end='')
            print(f'({a.get_name()}, {a.get_dice()})', end='')
            print(f'({b.get_name()}, {b.get_dice()})')

    def print_attack(board, attack):
        if attack is None:
            print('Attacking NONE')
        else:
            print('Attacking:', board.get_area(attack[0]).get_dice(), board.get_area(attack[1]).get_dice())
        print()

    def print_color(player_name):
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
        print()