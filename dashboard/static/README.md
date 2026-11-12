# Geographic basemap

`usa_110m.json` is the US topology extracted from Plotly's official
`dist/plotly-geo-assets.js` at revision
`b5e04cef30e6b2a1fb3e6750f21a06fc8b3cbbb2`:
https://github.com/plotly/plotly.js/blob/b5e04cef30e6b2a1fb3e6750f21a06fc8b3cbbb2/dist/plotly-geo-assets.js

The upstream MIT license is preserved in `LICENSE.plotly`.
Bundling the topology avoids runtime requests to Plotly's CDN. Streamlit serves
this directory using the repository's `.streamlit/config.toml`; the standalone
site builder copies it to `static/`.
