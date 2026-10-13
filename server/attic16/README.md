# attic16

The first 16.20 server (October 11, before the rewrite as `server/core/` + `server/main16.py`): `match16.py`
(session + match loop on the live recording), `bots16.py`, `spells16.py`, `shop16.py`, and the scratch
`x_client_side.py`. Kept for reference only; nothing imports them. They expect to sit next to `hero16.py` /
`world16.py`, which stay in `server/` because `server/lnp16.py` (the capture replay tool) still uses them, as does
`tools/build_forms16.py` with `structures16.py`.
