"""AIPunarartha — shared dashboard UI.

`ui/styles.py` holds the single global stylesheet, `ui/components.py` the
single set of shared builders, and `ui/nav.py` the one navigation definition
for the app. The view files at the top level of this package are routed by
`app.py` through `st.navigation`.

Everything is imported from its defining module (`ui.components`,
`ui.styles`, `ui.nav`) - this package deliberately exports nothing, so no
duplicate component set can creep back in.
"""