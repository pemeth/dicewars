import logging
import time
from pprint import pprint       # TODO REMOVE
from random import random

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
        
        self.attack_helper_attack_moves = []        # Moves to do before attack happen
        self.attack_helper_deffense_moves = []      # Moves to do after attack happen
        self.attack_move = None                     # Attack that will happen before or after transfer moves

        self.transfer_moves = []                    # Transfer moves to do in TRANSFER stage
        self.deffend_moves = []                     # Deffend moves to do in DEFFEND stage

    def ai_turn(self, board, nb_moves_this_turn, nb_transfers_this_turn, nb_turns_this_game, time_left):
        """AI agent's turn
        """
        
        # When there are attack_helper_attack_moves moves, do them before attack
        if len(self.attack_helper_attack_moves) > 0:
            # Pop one out, and do move
            move = self.attack_helper_attack_moves.pop()
            print("ATTACK_HELPING: ")
            AI_Debug.print_attack(board, move)
            return TransferCommand(move[0], move[1])

        # Do attack move after attack helper moves all helpers to increase attack
        if self.attack_move is not None:
            tmp_attack_move = self.attack_move
            print("ATTACK AFTER HELPING")
            AI_Debug.print_attack(board, tmp_attack_move)
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
                print("ATTACK_HELPING: ")
                AI_Debug.print_attack(board, move)
                return TransferCommand(move[0], move[1])

            AI_Debug.print_attack(board, attack)

            # When we possible attack, do it
            if attack is not None:
                return BattleCommand(attack[0], attack[1])

            # No attack found, change to deffend
            self.stage = 'deffend'

        if self.stage == 'deffend':
            # When there are defined deffend moves, go through them
            if len(self.deffend_moves):
                move = self.deffend_moves.pop()
                return TransferCommand(move[0], move[1])

            # Generate deffense moves, with maximum of 3 helping transfers
            self.deffend_moves = self.gen_deffense_moves(board, (6 - nb_moves_this_turn))

            # No more deffender moves, go to transfer stage
            if len(self.deffend_moves) == 0:
                self.stage = 'transfer'
        
        if self.stage == 'transfer':
            # When there are defined transfer moves, go through them
            if len(self.transfer_moves):
                move = self.transfer_moves.pop()
                return TransferCommand(move[0], move[1])

            # Generate transfer moves, with whats left after attack and deffend
            self.transfer_moves = self.gen_transfer_moves(board, (6 - nb_moves_this_turn))

            # No more moves
            if len(self.transfer_moves) == 0:
                self.stage = 'attack'
                return EndTurnCommand()

        print("INVALID STATE")
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
        our_border_areas_all = [area for area in board.get_player_border(self.player_name)]
        our_border_areas = [area for area in our_border_areas_all if area.can_attack()]
        
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
                    # Helper can only be the one that are not endangered by enemy
                    if not deffender_area in our_border_areas_all:
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

    def get_deffense_areas(self, board):
        pass

    def gen_deffense_moves(self, board, transfers_left):
        deffenses = self.get_deffense_areas(board)



        return []

    def gen_transfer_moves(self, board, transfers_left):
        # No more transfers left, end
        if transfers_left == 0:
            return []
        pass

        return []

    """-----------------------------------------------------------------------------------------
                                        ATTACK
    -----------------------------------------------------------------------------------------"""
    def get_attack(self, board, transfers_left):

        def recursively_find_helping_attack_path(attacker_dice, deffender_dice, last_helper, helpers_used, transfers_left):
            print("NO helping attack path")
            return []

        def find_helping_path(deff, previous_area, dice_count, threat, transfers_left):
            def is_helper_area(area_id):
                # Get neigbours
                neighs = board.get_area(area_id).get_adjacent_areas_names()

                # When one of neighbours is enemy, return False
                for neigh_id in neighs:
                    if board.get_area(neigh_id).get_owner_name() != self.player_name:
                        return False

                # Every neighbour is Ally
                return True

            if transfers_left == 0:
                print("NO helping deffense path, no transfers left")
                return []

            # Get possible helpers
            helpers = []

            # Generate helpers
            for helper_id in board.get_area(deff[0]).get_adjacent_areas_names():
                # Get id
                helper_area = board.get_area(helper_id)

                # When area is one of helper areas, or not the previous one
                if is_helper_area(helper_area.get_name()) and (previous_area is None or previous_area[0] != helper_area.get_name()):
                    helpers.append((helper_area.get_name(), helper_area.get_dice()))
                    continue

            # Look through helpers
            for helper in helpers:
                # Help is possible, use that
                if ((helper[1] + dice_count - 1) - threat[1]) >= -1:
                    return [(helper[0], deff[0])]
                else:
                    # Try to find helping path
                    help_path = find_helping_path(helper, deff, (dice_count + helper[1] - 1), threat, (transfers_left - 1))

                    # Path was not found, continue
                    if len(help_path) == 0:
                        continue

                    # Path was found
                    return help_path + [(helper[0], deff[0])]

            # There are transfers try to look for transfers
            return []

        def recursively_find_path(weak_att_deff, helper_id_dice, dice_count, threat, transfers_left):
            # No transfer left
            if transfers_left == 0:
                return []
            
            # Get helper area
            helping_area = board.get_area(helper_id_dice[0])

            # Get helpers that are not previous helper
            helper_ids = [area_id for area_id in helping_area.get_adjacent_areas_names() if area_id != weak_att_deff[0] and area_id != helper_id_dice[0]]
            helpers = []
            
            # Get helper areas, and convert to tuples
            for helper_id in helper_ids:
                helper = board.get_area(helper_id)

                # Ignore when there are enemies
                enemies = helper.get_adjacent_areas_names()

                # Check if there are any enemy around area, if they are ignore area
                if len([enemy_id for enemy_id in enemies if board.get_area(enemy_id).get_owner_name() != self.player_name]) != 0:
                    continue
                
                # Helper area without any enemies
                helpers.append((helper.get_name(), helper.get_dice()))

            # Sort by dice count
            helpers = sorted(helpers, reverse=True, key=lambda helper: helper[1])

            print("NEIGHB")
            print(weak_att_deff)
            print(helper_id_dice)
            pprint(helpers)


            # Check if some adjancent helper can help up
            for helper in helpers:
                # Can this helper help us ?
                if helper[1] > 1 and (helper[1] + dice_count) - threat[1] >= -1:
                    print ("RECURSIVE MOVE: ")
                    AI_Debug.print_attack(board, (helper[0], weak_att_deff[0]))
                    # Return transfer help move
                    return [(helper[0], helper_id_dice[0])]

                # Try to check recursively if someone can help us
                else:
                    # There is only 1 transfer left, find in next helper
                    if not transfers_left == 1:
                        continue

                    # Is there someone that can help us ?
                    recurse_help = recursively_find_path(
                        helper_id_dice,
                        (helper[0], helper[1]),
                        (helper[1] + dice_count),
                        threat,
                        (transfers_left - 1)
                    )

                    # No one to help
                    if len(recurse_help) == 0:
                        continue

                    # Someone can help us
                    return recurse_help + [(helper_id_dice[0], weak_att_deff[0])]
                pass

            # No helper found
            return []

        def find_helping_attack_path(attack, threat, transfers_left):
            """
                Generate helping attak path that will be done before attack

                Returns
                -------
                Int - Representing number of transfers consumed
            """

            # There are no helpers, attack is not possible
            if len(attack[2]) == 0:
                print("No helpers")
                return 0

            if transfers_left == 0:
                print("No tranfers left")
                return 0

            # There are helper, try to find path for helping us in attack
            for helper in attack[2]:
                # Recursively find attack path
                helpers = recursively_find_path(attack[0], helper, attack[0][1], threat, transfers_left)
                #helpers = []

                # Path not found
                if len(helpers) == 0:
                    continue

                # Path found, set helping attack path and attack
                self.attack_helper_attack_moves = helpers + [(helper[0], attack[0][0])]
                
                print("HELPING ATTACK PATH:")
                print(self.attack_helper_attack_moves)
                for h in self.attack_helper_attack_moves:
                    AI_Debug.print_attack(board, h)
                self.attack_helper_attack_moves.reverse()
                #input("?")
                return len(helpers)

            # Path not found
            return 0

        def future_threats(attacker, deffender):
            """
                Check if after attack we can be easily overtaken by surrounding enemies

                Returns
                -------
                None when no threat or Tuple(THREAD_ID, THREAD_DICE)
            """

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
                    print("FUTURE THREAT")
                    print(attacker_dices, enemy_area.get_dice())
                    print()
                    return (enemy_area.get_name(), enemy_area.get_dice())

            # No threats
            return None

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

            helpers = find_helping_path(
                (attack[0][0], 1),
                None,
                1,
                attack[1][1],
                transfers_left
            )

            if len(helpers) == 0:
                return False

            print("FOUND HELPING DEFFENSE PATH")
            
            self.attack_helper_deffense_moves = helpers
            pprint(self.attack_helper_deffense_moves)
            for h in self.attack_helper_deffense_moves:
                AI_Debug.print_attack(board, h)

            self.attack_helper_deffense_moves.reverse()


            return True

            # We did not found helper that is able to help us in 1 move, so go look through others in area
            for helper in attack[2]:
                
                #helpers = find_helping_path(attack[1][1], board.get_area(helper[0]), [], transfers_left)
                helpers = find_helping_path_recursively(
                    (attack[0][0], 1),
                    helper,
                    1,
                    attack[1][1],           # Use second highest deffender as threat, first we are attacking
                    transfers_left
                )

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

        #input("TEST")

        # Go through all possible attacks
        for attack in attacks:
            # Check if we are able to win first fight
            if AI_Utils.attack_win_loss(attack[0][1], attack[1][0][1]):
                
                # Get future threat
                future_threat = future_threats(attack[0], attack[1][0])

                # Future threat detected
                if future_threat is not None:
                    
                    # Find and create helping attack path
                    helping_path_cost = find_helping_attack_path(attack, future_threat, transfers_left)

                    # We found helping path
                    if helping_path_cost > 0:
                        print("FUTURE THREAT HELPING PATH")
                        #input("Ha?")
                        # Check if we will be able to keep our area after attack
                        if do_we_keep_area_after_attack(attack, (transfers_left - helping_path_cost)):
                            # We can do this move, return move
                            return (attack[0][0], attack[1][0][0])

                        # No invalidate helping attack path
                        self.attack_helper_attack_moves = []

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
                print("LOOSE")
                AI_Debug.print_attack(board, (attack[0][0], attack[1][0][0]))
                # Try to find helping attack path
                helping_path_cost = find_helping_attack_path(attack, attack[1][0], transfers_left)

                # We found one
                if helping_path_cost > 0:
                    print("UNABLE TO WIN HELPING PATH")
                    #input("Ha?")
                    # We can do this move, return move
                    return (attack[0][0], attack[1][0][0])

                    # Unable to keep our area after attack, invalidate helping attack path
                    self.attack_helper_attack_moves = []
        # No attack is possible
        return None

class AI_Utils:
    def attack_win_loss(atk, df):
        # Get probability
        prob = AI_Utils.attack_succcess_probability(atk, df)

        # We take those, these are almost 100% successfull
        if prob >= 0.8:
            return True

        # When we got atk 8, we take those in 95% of cases
        if atk == 8:
            return random() >= 0.05

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