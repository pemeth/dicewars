from ..utils import possible_attacks, probability_of_holding_area


def get_sdc_attack(board, player_name):
    attacks = []
    for source, target in possible_attacks(board, player_name):
        area_dice = source.get_dice()
        strength_difference = area_dice - target.get_dice()
        attack = [source.get_name(), target.get_name(), strength_difference]
        attacks.append(attack)

    attacks = sorted(attacks, key=lambda attack: attack[2], reverse=True)

    if attacks and attacks[0][2] >= 0:
        return attacks[0]
    else:
        return None


def get_transfer_to_border(board, player_name):
    # Get our area names that border with enemy neighbour
    border_names = [a.name for a in board.get_player_border(player_name)]

    # Get all our areas
    all_areas = board.get_player_areas(player_name)
    
    # Get only our areas that do not border with enemies
    inner = [a for a in all_areas if a.name not in border_names]

    # Loop through inner borders
    for area in inner:
        # Skip areas that have 1 dice
        if area.get_dice() < 2:
            continue

        # Loop through neigbours of current inner area
        for neigh in area.get_adjacent_areas_names():

            # When neigh is one of our areas and
            # 
            if neigh in border_names and board.get_area(neigh).get_dice() < 8:
                return area.get_name(), neigh

    return None

# Calculate loss
def areas_expected_loss(board, player_name, areas):
    hold_ps = [probability_of_holding_area(board, a.get_name(), a.get_dice(), player_name) for a in areas]
    return sum((1-p) * a.get_dice() for p, a in zip(hold_ps, areas))


def get_transfer_from_endangered(board, player_name):
    # Get our area names that border with enemy neighbour
    border_names = [a.name for a in board.get_player_border(player_name)]

    # Get all area names
    all_areas_names = [a.name for a in board.get_player_areas(player_name)]

    
    retreats = []

    # Loop through our areas that border with enemy
    for area in border_names:
        # Get area
        area = board.get_area(area)
        
        # Skip cant retreat
        if area.get_dice() < 2:
            continue
        
        # Loop through neighbours
        for neigh in area.get_adjacent_areas_names():
            # Skip when not our area
            if neigh not in all_areas_names:
                continue

            # Get neighbour area
            neigh_area = board.get_area(neigh)

            # Calculate expected loss of area
            expected_loss_no_evac = areas_expected_loss(board, player_name, [area, neigh_area])

            # Get dices
            src_dice = area.get_dice()
            dst_dice = neigh_area.get_dice()
            
            # Calculate how many dices will be moved
            dice_moved = min(8-dst_dice, src_dice - 1)

            # Decrease dices in area
            area.dice -= dice_moved

            # Increase dices in destination area
            neigh_area.dice += dice_moved

            # Calculate loss
            expected_loss_evac = areas_expected_loss(board, player_name, [area, neigh_area])
            
            # Set back data
            area.set_dice(src_dice)
            neigh_area.set_dice(dst_dice)

            # Append tuple to list
            retreats.append(((area, neigh_area), expected_loss_no_evac - expected_loss_evac))

    # Sort by expected loss diff
    retreats = sorted(retreats, key=lambda x: x[1], reverse=True)

    # When there are retreats
    if retreats:
        # Get the best possible
        retreat = retreats[0]

        # And when diff is higher than 0, do the retreat
        if retreat[1] > 0.0:
            return retreat[0][0].get_name(), retreat[0][1].get_name()

    return None
