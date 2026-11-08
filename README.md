# Fintools

## Tools

- [Backtesting](./Tool_Back_testing.html)
- [Investment simulator](./Tool_investment-simulator.html)
- [Crash buying simulator](./Tool_crash_buying_simulator_dbs_ocbc.html)
- [Admin: refresh Yahoo history](./admin.html)

## Data and refresh

Each tool reads historical daily closing prices from a JSON file in `data/`. The admin page lets you select one tool, several tools, or all three. It starts the `Refresh Yahoo price history` GitHub Actions workflow; the workflow retrieves Yahoo Finance chart history, validates it, and commits the selected JSON files. A failed retrieval stops the workflow before it commits updated files.

The refresh uses Yahoo Finance's undocumented chart endpoint. It provides daily market prices, not individual exchange transactions, and the endpoint may change.

To use the pages as a website, enable GitHub Pages for this repository in **Settings → Pages**, using the `main` branch and `/` (root). Then open `https://sgkjeajk.github.io/fintools/` or `https://sgkjeajk.github.io/fintools/admin.html`.

The admin page requires a fine-grained token scoped to this repository with **Actions: read and write** and **Contents: read and write**. The token is held only in the open page and is not saved in browser storage.
