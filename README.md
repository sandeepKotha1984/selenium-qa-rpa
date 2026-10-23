# Python Selenium RPA — Login and Multi-Form Submission

This is an RPA starter, not a pytest testing suite. It runs a browser workflow,
reads multiple form records from CSV, fills configured fields, submits each
record, and writes a CSV execution log.

## Important site distinction
The practice login site and QA Academy demo are separate public websites.
Logging into one does not authenticate you to the other. The workflow logs into
the practice login demo, then navigates to the QA Academy demo for form work.

## Setup on macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configure before form submission
1. Open `config.json`.
2. Review `login` and `forms` settings.
3. Visit the QA Academy demo page and inspect its current form fields using
   Chrome DevTools (right-click a field → Inspect).
4. Replace the example CSS selectors in `form_fields` and `submit_selector`
   with the actual selectors from the live page.
5. Set `success_selector` to a stable element/message that appears after a
   successful submission.
6. Keep `dry_run` set to `true` until the selectors have been checked. Set it
   to `false` only when you're ready to submit the demo form.

## Run
```bash
python rpa_bot.py
```

Headless mode for AWS EC2:
```bash
HEADLESS=1 python rpa_bot.py
```

## Input records
`input/form_submissions.csv` contains multiple records. Each row becomes one
form submission. Adapt its columns to match the actual form fields and update
`form_fields` in `config.json` accordingly.

## Output
The bot writes `output/rpa_run_YYYYMMDD_HHMMSS.csv` with a result row for every
submission attempt, plus browser screenshots for exceptions.

## Safety
Use only practice sites and data you are authorized to submit. Do not use real
credentials or bypass CAPTCHA/anti-bot controls. The public demo site may change,
so inspect the live selectors before enabling submission.
