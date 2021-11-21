import random

from dicewars.client.game.board import Board
from dicewars.client.game.area import Area

from dicewars.ai.utils import attack_succcess_probability

MIN_RAND_VAL = 1
MAX_RAND_VAL = 6

def heuristic_loss(attacker: Area, defender: Area):
    # Attacker wins when random value is in range <0, attack_change)
    if attack_succcess_probability(attacker.get_dice(), defender.get_dice()) > random.random():
        return (0, defender.get_dice())
    # Attacker looses
    else:
        return (attacker.get_dice() - 1, attacker.get_dice() // 4)

def possible_attacks(board: Board, player_name: int):
    attacks = []
    for area in board.get_player_border(player_name):
        if not area.can_attack():
            continue

        neighbours = area.get_adjacent_areas_names()
        attack_neigb = []

        for adj in neighbours:
            adjacent_area = board.get_area(adj)
            if adjacent_area.get_owner_name() != player_name:
                attack_neigb.append(adjacent_area)

        attacks.append((area, attack_neigb))
    return attacks

def get_possible_attacks(board: Board, player_name: int):
    attacks = possible_attacks(board, player_name)

    attack_weighted = []

    # Loop through all possible attacks
    for attack in attacks:
        attack_neigb = []
        cum_attacker_loss = 0
        cum_defender_loss = 0

        attacker, defenders = attack

        # Loop through all possible defenders
        for defender in defenders:
            attacker_loss, defender_loss = heuristic_loss(attacker, defender)
            attack_neigb.append({
                'attacker_loss': attacker_loss,
                'defender_loss': defender_loss,
                'defender': defender,
                'defender_name': defender.get_name()
            })

            cum_attacker_loss += attacker_loss
            cum_defender_loss += defender_loss

        attack_weighted.append({
            'attacker': attacker,
            'attacker_name': attacker.get_name(),
            'cum_attacker_loss': cum_attacker_loss,
            'cum_defender_loss': cum_defender_loss,
            'defenders': attack_neigb
        })

    return sorted(attack_weighted, key=lambda x: x['cum_defender_loss'] - x['cum_attacker_loss'], reverse=True)