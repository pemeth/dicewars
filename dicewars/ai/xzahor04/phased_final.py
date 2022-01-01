from copy import deepcopy
import logging
import time
import math
from pprint import pprint
from random import random
from collections import deque

from dicewars.client.ai_driver import BattleCommand, EndTurnCommand, TransferCommand
from dicewars.client.game.board import Board

# For typing hints
from typing import Dict, Tuple, List
from dicewars.client.game.area import Area

# TODO remove
from dicewars.ai.kb.stei_adt import AI as AI_STEI

class AI:
    def __init__(self, player_name, board, players_order, max_transfers):
        self.player_name = player_name
        self.logger = logging.getLogger('AI')

        self.stage = 'attack' # attack | deffend | transfer
        self.sims = ['full', 'deffend', 'do_nothing']
        self.MAX_TRANSFERS = max_transfers
        self.players_order = players_order

        # Print player color for debuging
        #AI_Debug.print_color(player_name)

        self.N_AREAS = sum(len(board.get_player_areas(player)) for player in players_order)

        self.attack_helper_attack_moves = []
        self.attack_helper_deffense_moves = []
        self.transfer_moves = []
        self.deffend_moves = []

        self.first_move_this_turn = True

        self.attack_move = None

    def ai_turn(self, board, nb_moves_this_turn, nb_transfers_this_turn, nb_turns_this_game, time_left, sim=None):
        """AI agent's turn
        """

        if self.first_move_this_turn and sim == None:
            # We are NOT in a simulation and this is our first move this round - simulate
            #verdict = self.maxn_entry(board, self.player_name, 3)
            verdict = self.alpha_beta_entry(board, self.player_name, 5)

            if verdict == 'full':
                self.stage = 'attack'
            elif verdict == 'deffend':
                self.stage = 'deffend'
            else: # verdict == 'do_nothing'
                self.first_move_this_turn = True
                return EndTurnCommand()

        if sim != None:
            # We are in a simulation
            if sim == 'full':
                self.stage = 'attack'
            elif sim == 'deffend':
                self.stage = 'deffend'
            else: # sim == 'do_nothing'
                self.first_move_this_turn = True
                return EndTurnCommand()


        # When there are deffend moves, do them
        if len(self.deffend_moves) > 0:
            move = self.deffend_moves.pop()
            self.first_move_this_turn = False
            return TransferCommand(move[0], move[1])

        # When there are attack_helper_attack_moves moves, do them before attack
        if len(self.attack_helper_attack_moves) > 0:
            # Pop one out, and do move
            move = self.attack_helper_attack_moves.pop()
            self.first_move_this_turn = False
            return TransferCommand(move[0], move[1])

        # Do attack move after attack helper moves all helpers to increase attack
        if self.attack_move is not None:
            tmp_attack_move = self.attack_move
            self.attack_move = None
            self.first_move_this_turn = False
            return BattleCommand(tmp_attack_move[0], tmp_attack_move[1])

        # When there are attack_helper_deffense_moves, do them after attack
        if len(self.attack_helper_deffense_moves) > 0:
            # Pop one out, and do move
            move = self.attack_helper_deffense_moves.pop()
            self.first_move_this_turn = False
            return TransferCommand(move[0], move[1])

        # Attacking stage
        if self.stage == 'attack':
            # Generate attack moves, with maximum of 3 helping transfers
            attack = self.get_attack(board, (4 - nb_transfers_this_turn))

            # When after attack there are attack_helper_moves, do them first
            if len(self.attack_helper_attack_moves) > 0:
                self.attack_move = attack
                # Pop one out, and do move
                move = self.attack_helper_attack_moves.pop()
                self.first_move_this_turn = False
                return TransferCommand(move[0], move[1])

            # When we possible attack, do it
            if attack is not None:
                self.first_move_this_turn = False
                return BattleCommand(attack[0], attack[1])

            # No attack found, change to deffend
            self.stage = 'deffend'

        if self.stage == 'deffend':
            # Generate deffense moves, with maximum of 3 helping transfers
            self.deffend_moves = self.gen_deffense_moves(board, (6 - nb_transfers_this_turn))

            # When there are defined deffend moves, go through them
            if len(self.deffend_moves) > 0:
                move = self.deffend_moves.pop()
                self.first_move_this_turn = False
                return TransferCommand(move[0], move[1])

            # No more deffender moves, go to transfer stage
            self.stage = 'transfer'

        if self.stage == 'transfer':
            # Generate transfer moves, with whats left after attack and deffend
            self.transfer_moves = self.gen_transfer_moves(board, (6 - nb_transfers_this_turn), self.player_name)

            # When there are defined transfer moves, go through them
            if len(self.transfer_moves):
                move = self.transfer_moves.pop()
                self.first_move_this_turn = False
                return TransferCommand(move[0], move[1])

            self.stage = 'attack'

        self.first_move_this_turn = True
        return EndTurnCommand()

    def alpha_beta_entry(self, board: Board, player_name, depth):
        """Entry point for the alpha-beta algorithm.
        """
        board_sim = deepcopy(board)
        idx = self.players_order.index(self.player_name)
        next_player = self.players_order[(idx + 1) % 4]
        best_sim = None

        turns, board_sim = self.simulate_turn(board_sim, player_name, self.sims[0])
        best_evaluation = self.alpha_beta(board_sim, next_player, depth - 1, self.N_AREAS)
        board_sim = self.unsimulate_turn(board_sim, turns)
        best_sim = self.sims[0]

        for sim_idx in range(1, len(self.sims)):
            if best_evaluation[idx] >= self.N_AREAS:
                # Alpha-Beta pruning
                return best_evaluation

            # Get evaluation for all simulation types
            turns, board_sim = self.simulate_turn(board_sim, player_name, self.sims[sim_idx])
            current_evaluation = self.alpha_beta(board_sim, next_player, depth - 1, self.N_AREAS - best_evaluation[idx])
            board_sim = self.unsimulate_turn(board_sim, turns)

            best_sim = self.sims[sim_idx] if current_evaluation[idx] > best_evaluation[idx] else best_sim
            best_evaluation = current_evaluation if current_evaluation[idx] > best_evaluation[idx] else best_evaluation

        return best_sim

    def alpha_beta(self, board: Board, player_name, depth, bound) -> List[int]:
        """Recursive alpha_beta algorithm implementation.
        """
        if depth <= 0:
            return self.eval_game(board)

        board_sim = deepcopy(board)
        idx = self.players_order.index(player_name)
        next_player = self.players_order[(idx + 1) % 4]

        turns, board_sim = self.simulate_turn(board_sim, player_name, self.sims[0])
        best_evaluation = self.alpha_beta(board_sim, next_player, depth - 1, self.N_AREAS)
        board_sim = self.unsimulate_turn(board_sim, turns)

        for sim_idx in range(1, len(self.sims)):
            if best_evaluation[idx] >= bound:
                # Alpha-Beta pruning
                return best_evaluation

            # Get evaluation for all simulation types
            turns, board_sim = self.simulate_turn(board_sim, player_name, self.sims[sim_idx])
            current_evaluation = self.alpha_beta(board_sim, next_player, depth - 1, self.N_AREAS - best_evaluation[idx])
            board_sim = self.unsimulate_turn(board_sim, turns)

            best_evaluation = current_evaluation if current_evaluation[idx] > best_evaluation[idx] else best_evaluation

        return best_evaluation

    def maxn_entry(self, board: Board, player_name, depth):
        """Entry point for the maxn algorithm.
        """
        board_sim = deepcopy(board)
        idx = self.players_order.index(self.player_name)
        next_player = self.players_order[(idx + 1) % 4]
        best_evaluation = [-math.inf for _unused in self.players_order]
        best_sim = None

        for sim in self.sims:
            # Get evaluation for all simulation types
            turns, board_sim = self.simulate_turn(board_sim, player_name, sim)
            current_evaluation = self.maxn(board_sim, next_player, depth - 1)
            board_sim = self.unsimulate_turn(board_sim, turns)

            best_sim = sim if current_evaluation[idx] > best_evaluation[idx] else best_sim
            best_evaluation = current_evaluation if current_evaluation[idx] > best_evaluation[idx] else best_evaluation

        return best_sim

    def maxn(self, board: Board, player_name, depth) -> List[int]:
        """Recursive maxn algorithm implementation.
        """
        if depth <= 0:
            return self.eval_game(board)

        # Initialize to negative infinity
        best_evaluation = [-math.inf for _unused in self.players_order]

        board_sim = deepcopy(board)
        idx = self.players_order.index(player_name)
        next_player = self.players_order[(idx + 1) % 4]

        for sim in self.sims:
            # Get evaluation for all simulation types
            turns, board_sim = self.simulate_turn(board_sim, player_name, sim)
            current_evaluation = self.maxn(board_sim, next_player, depth - 1)
            board_sim = self.unsimulate_turn(board_sim, turns)

            best_evaluation = current_evaluation if current_evaluation[idx] > best_evaluation[idx] else best_evaluation

        return best_evaluation

    def eval_game(self, board: Board) -> List[int]:
        """Evaluates the game for each player and returns.

        Returns
        -------
        A list of evaluations for each player in the same order as `self.player_order`.
        """
        # TODO better evaluation (mayhaps based on the sum of border areas' hold probability)
        return [len(board.get_player_areas(player)) for player in self.players_order]

    def unsimulate_turn(self, board: Board, turns: List[Dict]) -> Board:
        """Reverts changes made to `board` by `simulate_turn()`.
        """
        while turns:
            turn = turns.pop()
            board.get_area(turn['src']['name']).set_dice(turn['src']['dice_before'])
            board.get_area(turn['dst']['name']).set_dice(turn['dst']['dice_before'])
            board.get_area(turn['dst']['name']).set_owner(turn['dst']['owner_before'])

        return board

    def simulate_turn(self, board: Board, player_name, sim: str) -> Tuple[List[Dict], Board]:
        """Simulate a turn for `player_name` on `board`.
        """
        ######################## WARNING: TODO #################################
                    # TODO WE PROLLY CANT USE ANOTHER AI
        ########################################################################
        #ai_stei = AI_STEI(player_name, board, self.players_order, self.MAX_TRANSFERS)

        # Use our AI
        ai = AI(player_name, board, self.players_order, self.MAX_TRANSFERS)

        nb_moves = 0
        nb_transfers = 0

        turns = []

        battle_won = lambda atk, df: random() < AI_Utils.attack_succcess_probability(atk, df)

        # These are constant for this project
        BATTLE_WEAR = 4
        MAX_DICE_PER_AREA = 8

        while True:
            turn = ai.ai_turn(board, nb_moves, nb_transfers, 0, 5, sim)

            # What follows is a slightly simplified game logic from dicewars.server.game

            if isinstance(turn, EndTurnCommand):
                break

            nb_moves += 1

            src = turn.source_name
            dst = turn.target_name
            src_dice_before = board.get_area(src).get_dice()
            src_dice_after = 0

            dst_dice_before = board.get_area(dst).get_dice()
            dst_owner_before = board.get_area(dst).get_owner_name()
            dst_dice_after = 0
            dst_owner_after = dst_owner_before

            turn_type = None

            if isinstance(turn, BattleCommand):
                turn_type = 'battle'
                src_dice_after = 1 # regardless of the battle outcome, 1 dice remains

                if battle_won(src_dice_before, dst_dice_before):
                    dst_dice_after = src_dice_before - 1
                    dst_owner_after = board.get_area(src).get_owner_name()
                else:
                    battle_wear = src_dice_before // BATTLE_WEAR
                    dst_dice_after = max(1, dst_dice_before - battle_wear)

            elif isinstance(turn, TransferCommand):
                turn_type = 'transfer'
                nb_transfers += 1
                dice_moved = min(MAX_DICE_PER_AREA - dst_dice_before, src_dice_before - 1)

                src_dice_after = src_dice_before - dice_moved
                dst_dice_after = dst_dice_before + dice_moved

            board.get_area(src).set_dice(src_dice_after)
            board.get_area(dst).set_dice(dst_dice_after)
            board.get_area(dst).set_owner(dst_owner_after)

            turns.append({
                'type': turn_type,
                'src': {
                    'name': src,
                    'dice_before': src_dice_before,
                    'dice_after': src_dice_after
                },
                'dst': {
                    'name': dst,
                    'dice_before': dst_dice_before,
                    'dice_after': dst_dice_after,
                    'owner_before': dst_owner_before,
                    'owner_after': dst_owner_after
                }
            })

        return turns, board

    def gen_helping_defense_path(self, board, deffender, dice_count, ignore_areas, threat, transfers_left):
        # No transfers left
        if transfers_left <= 0:
            return []

        #
        for helper in AI_Utils.get_helpers(board, deffender, ignore_areas, self.player_name):
            # Found helper that is able to help, generate move
            if helper[1] > 1 and ((dice_count + helper[1] - 1) - threat[1]) >= -1:
                return [(helper[0], deffender[0])]

            # Not found, try recursive search
            else:
                # Not enough transfers, atleast 2 needed
                if transfers_left <= 1:
                    continue

                # Generate path
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
                    # Not endangered by enemy, add to helpers
                    if not deffender_area in our_border_areas:
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

            # Add enemy with the highest dice count
            endangered_areas.append(
                (
                    (area.get_name(), area.get_dice()),
                    enemies[0]
                )
            )

        # Sort by difference between ENEMY and our DICE count
        return sorted(endangered_areas, key=lambda endangered_area: endangered_area[0][1] - endangered_area[1][1])


    def get_attack(self, board, transfers_left):
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
                    return [(helper[0], attacker[0])]
                # Not found, try recursive search
                else:
                    # There are needed atleast 2 transfers
                    if transfers_left <= 1:
                        continue

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
                    return path + [(helper[0], attacker[0])]

            return []

        def find_helping_attack_path(attack, transfers_left):
            # No transfers left, no one can help us
            if transfers_left <= 0:
                return False

            # There are no helpers, attack is not possible
            if len(attack[2]) == 0:
                return False

            # Calculate uplated value of attack with max value of 8
            updated_attack = AI_Utils.clamp_number_of_dices(attack[2][0][1] + (attack[0][1] - 1))   # -1 because it is transfer, we left 1 behind

            # Try the first helper, he needs to be higher than 1, when we possibly won check future
            if attack[0][1] > 1 and AI_Utils.attack_win_loss(updated_attack, attack[1][0][1]):
                # Check if we will be able to keep our area after attack
                if do_we_keep_area_after_attack(attack, (transfers_left - 1)):  # One transfer is being used to increase dice for attacking

                    # We win check future threats
                    possible_threat = future_threats((attack[0][0],updated_attack), attack[1][0])

                    # When there is no future threat, generate heping move, before attack
                    if possible_threat is None:
                        self.attack_helper_attack_moves = [(attack[2][0][0], attack[0][0])]
                        return True

                    # There is future threat, we cant help in 1 move, go check other moves
                    # Clean up helpers, after we are not making any move (do_we_keep_area_after_attack, generated helpers)
                    self.attack_helper_deffense_moves = []

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

            # Flip so we can pop it out
            attack_path.reverse()

            # Path found, set and return True
            self.attack_helper_attack_moves = attack_path
            return True

        def future_threats(attacker, deffender):
            # Attacker dice after attack
            attacker_dices = attacker[1] - 1

            # Get deffender area
            deffender_area = board.get_area(deffender[0])

            enemy_found = None

            # Find enemy with the highest dice count
            for enemy_id in deffender_area.get_adjacent_areas_names():
                # Get area
                enemy_area = board.get_area(enemy_id)

                # Skip our areas
                if enemy_area.get_owner_name() == self.player_name:
                    continue

                # Skip enemies with 1 dice count
                if enemy_area.get_dice() == 1:
                    continue

                # We found enemy with more dice
                if enemy_found is None or enemy_found[1] < enemy_area.get_dice():
                    enemy_found = (enemy_area.get_name(), enemy_area.get_dice())

            # Threat found
            if enemy_found is not None and (attacker_dices - enemy_found[1]) < -1:
                return enemy_found

            # No threats
            return None

        def do_we_keep_area_after_attack(attack, transfers_left):
            # Only 1 possible enemy, the one we are attacking, no one to endanger us
            if len(attack[1]) <= 1:
                return True

            # There are more enemies, check the second one, when it is 1, no one to endanger us
            if attack[1][1][1] == 1:    # Enemy array is sorted by dice count
                return True

            # No more transfers left, previous check is false, there is someone that can endanger us
            # but we can do nothing
            if transfers_left <= 0:
                return False

            # There are possible transfers

            # When there are no helpers, we cant do anything
            if len(attack[2]) == 0:
                return False

            # We found helper that is able to help, he needs to have more than 1 dice
            if attack[2][0][1] > 1 and (attack[2][0][1] - attack[1][1][1]) >= -1:
                self.attack_helper_deffense_moves = [(attack[2][0][0], attack[0][0])]
                return True

            # We did not found helper that is able to help us in 1 move, so go look through others in area
            helpers = self.gen_helping_defense_path(
                board,
                (attack[0][0], 1),
                1,
                [attack[0][0]],
                attack[1][1],
                transfers_left
            )

            # No path found, no one can help us
            if len(helpers) == 0:
                return False

            # Reverse path so we can pop it out
            helpers.reverse()

            # Set new path
            self.attack_helper_deffense_moves = helpers
            return True

        # Get all areas we border with enemies that can attack, and return the best move
        attacks = self.get_possible_attacks(board)

        # Print out possible attacks
        #AI_Debug.print_possible_attacks(attacks)

        # Go through all possible attacks
        for attack in attacks:
            # Check if we are able to win first fight
            if AI_Utils.attack_win_loss(attack[0][1], attack[1][0][1]):
                # Check if we will be able to keep our area after attack
                if do_we_keep_area_after_attack(attack, transfers_left):

                    # Check possible threat
                    possible_threat = future_threats(attack[0], attack[1][0])

                    # There is no threat we can do the attack
                    if possible_threat is None:
                        # Return attack
                        return (attack[0][0], attack[1][0][0])

                    # There is threat, try to find attack path, take into account, we can have deffense moves
                    if find_helping_attack_path(attack, (transfers_left - len(self.attack_helper_deffense_moves))):
                            # Return attack
                        return (attack[0][0], attack[1][0][0])

                    # Path not found, invalide attack helper deffense moves
                    self.attack_helper_deffense_moves = []

                # We are unable to keep our area, try to find another attack
                continue

            # We are unable to win, try to find helpers that can help us, if not attack is impossible
            else:
                # Try to find helping attack path
                if find_helping_attack_path(attack, transfers_left):
                    # Attack was found
                    return (attack[0][0], attack[1][0][0])

        # No attack is possible
        return None

    # DONE
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
    # DONE
    def gen_transfer_moves(self, board: Board, transfers_left: int, player_name: int) -> List[Tuple[int, int]]:
        """Generate ONE transfer from areas that aren't close to the borders.

        Returns
        -------
        A list of a single transfer as a tuple of area names (source, destination)
        or an empty list if no viable transfer was found.
        """
        # No more transfers left, end
        if transfers_left <= 0:
            return []

        all_areas = board.get_player_areas(player_name)
        border_areas = board.get_player_border(player_name)
        enclosed_areas = list(set(all_areas).difference(border_areas))

        def score_border_area(area: Area):
            """Used for sorting the border areas.
            """
            score = area.get_dice()

            neighbour_score = sum(
                [board.get_area(neigh).get_dice() for neigh in area.get_adjacent_areas_names() if board.get_area(neigh).get_owner_name() == player_name]
            )
            neighbour_score *= 0.5 # weighting neighbours

            score += neighbour_score
            return score

        # Sort border_areas in ascending order by a "defensive" score given to its surrounding area
        border_areas.sort(key=score_border_area)

        if len(all_areas) >= len(board.areas) // 2:
            # If we control few areas, support borders more directly
            take_from_far_away = False
        else:
            # If we control many areas, move dice towards border from far away
            take_from_far_away = True

        # Sort enclosed areas by their distance from the border
        enclosed_areas.sort(key=lambda area: AI_Utils.distance_from_border(board, area, player_name), reverse=take_from_far_away)

        deferred_transfer = (0, 0)
        deferred_dice = 0
        deferred_path = []

        # Try to move dices closer
        for border_area in border_areas:
            deferred_dice = 0
            for enclosed_area in enclosed_areas:
                if enclosed_area.get_dice() == 1:
                    # No dice to transfer
                    #print(enclosed_area.get_name(), " no dice")
                    continue

                path, distance = AI_Utils.path_from_to(board, enclosed_area, border_area, player_name, not_along_borders=True)

                if distance == -1:
                    # Not found
                    #print(enclosed_area.get_name(), " not found")
                    continue

                if board.get_area(path[1]).get_dice() == 8:
                    # Don't pass to full area
                    #print(enclosed_area.get_name(), " no pass to full")
                    continue

                if deferred_dice == 0:
                    # This is done only once - the first time this code is reached.
                    # The first found move is deferred in case a better one is found.
                    deferred_dice = board.get_area(path[0]).get_dice()
                    deferred_transfer = (path[0], path[1])
                    deferred_path = path
                    continue

                # Pick the better transfer between the current and the deferred one
                if deferred_dice < board.get_area(path[0]).get_dice():
                    return [(path[0], path[1])]
                else:
                    return [deferred_transfer]

        # There are some transfers left, but no transfer was done

        if len(deferred_path):
            # Try the deferred move if one exists
            return [(deferred_path[0], deferred_path[1])]

        def_moves = self.gen_deffense_moves(board, transfers_left)
        if len(def_moves):
            # Try a defensive move if one exists
            move = def_moves.pop()
            return [move]

        return []

class AI_Utils:
    # TODO all methods of AU_Utils are static - decorate them with @staticmethod!
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

        # Sort by dice count
        return sorted(helpers, reverse=True, key=lambda helper: helper[1])

    def clamp_number_of_dices(n):
        if n > 8:
            return 8
        else:
            return n

    @staticmethod
    def distance_from_border(board: Board, area: Area, player_name: int) -> int:
        """Find the distance between `area` and the closest border.

        Returns
        -------
        The distance to the closest border. Returns -1 if border is not found.
        """
        area_name = area.get_name()

        visited = set()
        to_be_visited = [area_name]
        distance = 0

        if AI_Utils.border_with_enemy(board, area, player_name):
            return distance

        while to_be_visited:
            search_level_size = len(to_be_visited)

            while search_level_size != 0:
                current_area_name = to_be_visited.pop(0)

                for neighbour_name in board.get_area(current_area_name).get_adjacent_areas_names():
                    neighbour = board.get_area(neighbour_name)
                    if AI_Utils.border_with_enemy(board, neighbour, player_name):
                        return distance + 1

                    if neighbour_name in visited or neighbour_name in to_be_visited:
                        continue

                    to_be_visited.append(neighbour_name)

                search_level_size -= 1
                visited.add(current_area_name)

            distance += 1

        # border was not found (?)
        return -1

    @staticmethod
    def path_from_to(board: Board, src: Area, dst: Area, player_name: int, not_along_borders=False) -> Tuple[List[int], int]:
        """Get the path and distance from `src` to `dst`.

        Done with a BFS/Dijsktra hybrid algorithm.

        Parameters
        ----------
        not_along_borders : bool
            If True, then the algorithm will not return a path that goes
            through a border area.

        Returns
        -------
        A tuple containing the path from `src` to `dst` and the distance of the path.
        """
        all_areas = board.get_player_areas(player_name)

        previous = {area.get_name(): None for area in all_areas}

        src_name = src.get_name()
        dst_name = dst.get_name()

        visited = set()
        to_be_visited = [src_name]

        if src_name == dst_name:
            path = AI_Utils.shortest_path(previous, dst_name)
            return (path, len(path) - 1)

        while to_be_visited:
            search_level_size = len(to_be_visited)

            while search_level_size != 0:
                current_area_name = to_be_visited.pop(0)

                for neighbour_name in board.get_area(current_area_name).get_adjacent_areas_names():
                    if neighbour_name == dst_name:
                        # Found the destination
                        previous[neighbour_name] = current_area_name
                        path = AI_Utils.shortest_path(previous, dst_name)
                        return (path, len(path) - 1)

                    if neighbour_name in visited or neighbour_name in to_be_visited:
                        # Has been processed or already is in queue to be processed
                        continue

                    if board.get_area(neighbour_name).get_owner_name() != player_name:
                        # Only care about "our" areas
                        continue

                    if not_along_borders and AI_Utils.border_with_enemy(board, board.get_area(neighbour_name), player_name):
                        # Don't want to lead a path along borders
                        continue

                    previous[neighbour_name] = current_area_name
                    to_be_visited.append(neighbour_name)

                search_level_size -= 1
                visited.add(current_area_name)

        # Destination was not found
        return ([], -1)

    @staticmethod
    def shortest_path(previous: Dict[int, int], dst: int) -> List[int]:
        """A utility function for path backtracking used by `path_from_to()`.
        """
        path = [dst]
        step = dst
        while previous[step] != None:
            path.append(previous[step])
            step = previous[step]
        path.reverse()

        return path

    def border_with_enemy(board, area, player_name):
        # Get all neigbour areas
        neighbours = area.get_adjacent_areas_names()

        # Check every area, and when one is
        for neighbour in neighbours:
            neigh_area = board.get_area(neighbour)

            # When one of the
            if neigh_area.get_owner_name() != player_name:
                return True

        return False

    def attack_win_loss(atk, df):
        # Get probability
        prob = AI_Utils.attack_succcess_probability(atk, df)

        # We take those, these are almost 100% successfull
        if prob >= 0.8 or atk == 8:
            return True

        # We take those in 95% of cases
        if prob >= 0.6:
            return random() >= 0.05

        # Otherwise there is 50/50 chance
        if prob >= 0.45:
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

    def print_moves(board, moves):
        for m in moves:
            AI_Debug.print_move(board, m)

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