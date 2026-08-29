# VeriHire frontend

A responsive frontend prototype built with HTML, CSS, and JavaScript.

## Run

Open `index.html` directly in a browser, or serve the folder with any static server. For example, if Python is installed:

```powershell
python -m http.server 8080
```

Then visit `http://127.0.0.1:8080/?v=10#/`.

Navigation uses hash routes (for example `#/dashboard` and `#/verify`) so every view works on a basic static server without extra routing configuration.

## Included views

- Landing, login, and signup
- Candidate dashboard
- Job search and job details
- Animated private eligibility verification
- Applications and status timeline
- Employer dashboard and privacy-safe candidate details
- Employer jobs/candidates placeholders
- Profile and privacy settings
