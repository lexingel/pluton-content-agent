name: Generate Content

on:
  schedule:
    # 08:00 Türkiye saati (UTC+3) = 05:00 UTC.
    - cron: "0 5 * * *"
  workflow_dispatch: {}  # triggered by the admin panel's "Yeni İçerik Üret" button

jobs:
  generate:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install anthropic requests

      - name: Generate and stage content
        working-directory: content_agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          ANTHROPIC_WORKSPACE_ID: ${{ secrets.ANTHROPIC_WORKSPACE_ID }}
          FAL_KEY: ${{ secrets.FAL_KEY }}
          SFTP_HOST: ${{ secrets.SFTP_HOST }}
          SFTP_USER: ${{ secrets.SFTP_USER }}
          SFTP_PASSWORD: ${{ secrets.SFTP_PASSWORD }}
          SFTP_REMOTE_BLOG_DIR: ${{ secrets.SFTP_REMOTE_BLOG_DIR }}
        run: python generate_and_stage.py
