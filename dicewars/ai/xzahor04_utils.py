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
        attacker_loss = 0
        defender_loss = 0

        # Loop through all possible defenders
        for defender in attack[1]:
            loss = heuristic_loss(attack[0], defender)
            attack_neigb.append({'attacker_loss': loss[0], 'defender_loss': loss[1], 'defender': defender})

            attacker_loss += loss[0]
            defender_loss += loss[1]

        attack_weighted.append({
            'attacker': attack[0],
            'attacker_loss': attacker_loss,
            'defender_loss': defender_loss,
            'defenders': attack_neigb
        })

    return sorted(attack_weighted, key=lambda x: x['defender_loss'] - x['attacker_loss'], reverse=True)