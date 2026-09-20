# Vendored Pokémon Showdown battle renderer

This directory contains the minimum browser renderer/data/CSS subset used to
display the official Pokémon Showdown battle scene without an iframe. The
source of the renderer is the [official Pokémon Showdown client]
(https://github.com/smogon/pokemon-showdown-client); the integration pattern
was verified against Nidozo commit `326fa2a4a943b59bf3ea1050dac00b26f787a3d2`.

The reference bundle was fetched from the official Showdown CDN on 2026-06-21
by that project. The files are kept in the CDN-compatible `js/lib`, `js`,
`data`, and `style` layout so they can be loaded as ordinary static scripts.
No Nidozo application, React, LLM, or Electron code is included here.

## License and attribution

The official client repository currently describes the client as AGPLv3. The
compiled battle engine and data files in this exact subset retain their
upstream headers; those headers identify MIT-licensed battle-engine/data files
where applicable. `style/battle.css` retains its GPLv2 notice. `battle-log.css`
has no standalone header in the fetched bundle and remains an official client
file. These notices are not a relicensing grant: users distributing this
project should review and comply with the applicable upstream terms.

The upstream source and license are authoritative:

- https://github.com/smogon/pokemon-showdown-client
- https://github.com/smogon/pokemon-showdown-client/blob/master/LICENSE

The scene's sprites, icons, backgrounds, and move-effect textures are loaded
from official Showdown resources at `https://play.pokemonshowdown.com/` using
the runtime configuration in `showdown-renderer.js`. This repository does not
claim ownership of those resources.
