import logging
import random
import time

from dicewars.client.ai_driver import BattleCommand, EndTurnCommand
from dicewars.ai.xzahor04_utils import possible_attacks, get_possible_attacks
from dicewars.ai.utils import possible_attacks as pa

class AI:
    def __init__(self, player_name, board, players_order, max_transfers):
        self.player_name = player_name
        self.logger = logging.getLogger('AI')

        self.stage = 'attack'   # ATTACK | DEFEND | TRANSFER
        self.MIN_DICE_DIFF = 3
        self.MAX_TRANSFERS = max_transfers

    def ai_turn(self, board, nb_moves_this_turn, nb_transfers_this_turn, nb_turns_this_game, time_left):
        """AI agent's turn

        """

        # Attack stage
        if self.stage == 'attack':

            a = get_possible_attacks(board, self.player_name)
            for b in a:
                print(f"attacker_name: {b['attacker_name']}")
                print(f"cum_attacker_loss: {b['cum_attacker_loss']}")
                print(f"cum_defender_loss: {b['cum_defender_loss']}")
                print(f"defenders: {b['defenders']}")
                print()
                print()

        # Defend stage
        elif self.stage == 'defend':
            pass

        # Transfer stage
        else:
            pass

        time.sleep(120)

        if nb_moves_this_turn == 2:
            self.logger.debug("I'm too well behaved. Let others play now.")
            print("I'm too well behaved. Let others play now.")
            return EndTurnCommand()

        """ attacks = list(possible_attacks(board, self.player_name))
        if attacks:
            source, target = random.choice(attacks)
            return BattleCommand(source.get_name(), target.get_name())
        else:
            self.logger.debug("No more possible turns.")
            print("No more possible turns.")
            return EndTurnCommand() """

        return EndTurnCommand()
