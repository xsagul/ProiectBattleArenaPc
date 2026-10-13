"""The 16.20 game server's core: the simulation of a match (game.py) and everything it is made of.

    gamedata.py   the game's own data (map, units, champions) as the server reads it
    packets.py    every server packet the simulation writes, in the live server's forms (the one place bytes are made)
    units.py      the unit model: stats, health, movement, basic attacks, replication of changed values
    game.py       the match: clock, 30 Hz frame, registries, scheduler, frame order, rewards, deaths
    ai.py         lane minions, turrets, jungle monsters
    heroes.py     champions: orders, levels, skill points, economy, death and return
    spells.py     the generic spell system (data-driven casts, missiles, areas, buffs)
    shop.py       items
    bots.py       champions nobody plays
    session.py    one client's connection: the three parts of the real server's start, its requests
"""
