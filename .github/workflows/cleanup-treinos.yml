# .github/workflows/cleanup-treinos.yml
name: Cleanup Treinos Duplicatas

on:
  workflow_dispatch:  # disparo manual pelo GitHub

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install notion-client python-dotenv
      - run: DRY_RUN=false python cleanup-duplicatas-treinos.py
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          NOTION_TREINOS_DB_ID: ${{ secrets.NOTION_TREINOS_DB_ID }}
