# SMTP Setup (Gmail / SendGrid)

This project supports email providers via environment variables.

## 1. Configure environment variables

Use `.env.example` as reference and set variables in your deployment environment:

- `EMAIL_PROVIDER`: `gmail`, `sendgrid`, `smtp`, or `console`
- `DEFAULT_FROM_EMAIL`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- Optional: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`

## 2. Gmail setup

- Set:
  - `EMAIL_PROVIDER=gmail`
  - `EMAIL_HOST_USER=<your_gmail>`
  - `EMAIL_HOST_PASSWORD=<gmail_app_password>`
  - `DEFAULT_FROM_EMAIL=<your_gmail>`
- Use Google App Password (normal account password usually will not work).

## 3. SendGrid setup

- Set:
  - `EMAIL_PROVIDER=sendgrid`
  - `EMAIL_HOST_USER=apikey`
  - `EMAIL_HOST_PASSWORD=<sendgrid_api_key>`
  - `DEFAULT_FROM_EMAIL=<verified_sender_email>`

## 4. Local development

- Keep `EMAIL_PROVIDER=console` to print emails in terminal.
