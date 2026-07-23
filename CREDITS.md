# Credits & Attribution

## Inspiration
Worldlens was inspired by the **idea** behind
[`worldmonitor`](https://github.com/koala73/worldmonitor) by **Elie Habib** — a real-time
global-intelligence dashboard. Worldlens is an **independent, from-scratch reimplementation**
with a different tech stack, architecture, and data pipeline. **No source code from the original
project was used or copied**, and the two projects share no code. All the code in this repository
was written from scratch and is released under the MIT license.

## Open-source software
| Project | Author | License |
|---------|--------|---------|
| [globe.gl](https://github.com/vasturiano/globe.gl) | Vasco Asturiano | MIT |
| [solar-calculator](https://github.com/vasturiano/solar-calculator) | Vasco Asturiano | ISC |
| [three.js](https://github.com/mrdoob/three.js) | mrdoob & contributors | MIT |
| [satellite.js](https://github.com/shashwatak/satellite-js) | Shashwat Kandadai & contributors | MIT |

The day/night terminator and cloud layers adapt globe.gl's MIT-licensed examples
(`day-night-cycle`, `clouds`).

## Data & assets
| Asset | Source | Terms |
|-------|--------|-------|
| Planet & moon textures | [threex.planets](https://github.com/jeromeetienne/threex.planets) (Jérôme Étienne) | MIT |
| Country borders (50 m) | [Natural Earth](https://www.naturalearthdata.com/) | Public domain |
| Earth day/night/cloud textures | three-globe examples | MIT |
| Earthquakes | [USGS](https://earthquake.usgs.gov/) | Public domain (US Gov) |
| Natural hazards | [NASA EONET](https://eonet.gsfc.nasa.gov/) | Open |
| Disaster alerts | [GDACS](https://www.gdacs.org/) | Open (EC/UN) |
| Weather & air quality | [Open-Meteo](https://open-meteo.com/) | CC-BY 4.0 |
| Space weather | [NOAA SWPC](https://www.swpc.noaa.gov/) | Public domain (US Gov) |
| Live aircraft | [adsb.lol](https://adsb.lol/) | Open / ODbL |
| Satellite TLEs | [Celestrak](https://celestrak.org/) | Free for non-commercial use |
| Markets | [Yahoo Finance](https://finance.yahoo.com/), [CoinGecko](https://www.coingecko.com/) | Per provider terms |

Worldlens only **reads** public endpoints and stores nothing but a local JSON snapshot. Each data
provider's own terms of use apply to the data itself.
