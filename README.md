# MediSave India

**A medicine discovery and price comparison demo for India.** Search a sample medicine catalogue, compare illustrative offers from local and online providers, and explore community medicine requests.

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-API%20%26%20server-3776AB?logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-frontend-F7DF1E?logo=javascript&logoColor=222)
![Java](https://img.shields.io/badge/Java-21%20backend-ED8B00?logo=openjdk&logoColor=white)

> **Prototype notice:** Prices and pharmacy offers in the bundled CSV files are fictional sample data. They are not live quotes, verified stock, or medical advice. Symptom information is a small, offline prototype and is not clinically validated. It does not diagnose conditions or recommend medicines or dosages. Confirm product details with a pharmacy and consult a healthcare professional for personal advice. For emergencies in India, call 112.

## Contents

- [Features](#features)
- [Technology](#technology)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Firebase configuration](#firebase-configuration)
- [Deploy](#deploy)
- [API routes](#api-routes)
- [Project structure](#project-structure)
- [Data and limitations](#data-and-limitations)
- [License](#license)

## Features

- Search sample medicine brands, ingredients, and strengths, with spelling suggestions.
- Rank results using a catalogue-fitted TF-IDF retrieval model with word, phrase, and character n-grams, plus a fuzzy spelling fallback.
- Compare illustrative INR pack prices across sample local pharmacies and online stores.
- Sort nearby sample pharmacies using browser location, when enabled.
- Browse general, source-linked self-care information for supported symptom phrases.
- Open provider-scoped Google searches when a medicine is missing from the sample catalogue.
- Sign in and create or browse community medicine requests.
- Use responsive pages with dark mode.

## Technology

| Area | Technologies |
| --- | --- |
| Frontend | HTML, CSS, Tailwind CSS, JavaScript |
| Local server and API | Python |
| Optional standalone backend | Java 21, Spring Boot, Maven |
| Authentication and deployed data | Firebase Authentication, Firebase Admin SDK, Cloud Firestore |
| Local request storage | SQLite |
| Hosting and serverless routes | Vercel |
| Catalogue data | CSV |

## Architecture

- `public/` contains the browser application and built CSS.
- `dev_server.py` serves the app locally and provides the local development API behavior.
- `api/` contains Python serverless route handlers used by Vercel. `vercel.json` maps public `/api/v1/...` paths to these handlers.
- `medisave/` contains shared Python application services for search, provider data, Firebase, symptoms, and local requests.
- `backend/` contains an optional Java 21 / Spring Boot service and Dockerfile. The Vercel routes are implemented in Python; the Java service is a separate backend option.
- Local community requests use SQLite. Deployed community requests and catalogue integration use Firestore through the Firebase Admin SDK.

## Quick start

Prerequisites: Python and Node.js/npm (Node.js is only needed to rebuild the Tailwind stylesheet).

From the repository root:

```powershell
python -m pip install -r requirements.txt
python dev_server.py
```

Open [http://localhost:8787](http://localhost:8787). To use a different port, run `python dev_server.py 8787` (replace `8787` with the desired port).

Medicine search works against the bundled catalogue without Firebase configuration. Sign-in and sign-up require Firebase web configuration; see [Firebase configuration](#firebase-configuration).

To rebuild the CSS after changing Tailwind classes or `styles.src.css`:

```powershell
npm install
npm run build:css
```

## Firebase configuration

Copy `.env.example` to `.env.local`, then fill in the Firebase Web App values. Enable the Email/Password provider in Firebase Authentication for sign-in and sign-up.

```text
FIREBASE_API_KEY=
FIREBASE_AUTH_DOMAIN=
FIREBASE_PROJECT_ID=
FIREBASE_APP_ID=
```

Local community requests are stored in `data/local_medisave.sqlite3`. For deployed Firestore-backed requests and catalogue data, configure `FIREBASE_SERVICE_ACCOUNT_JSON` with a Firebase Admin service account JSON value in the server environment. Keep this credential server-side; never put it in frontend code or commit it to source control.

Enable Firestore and review the access policy in [`firestore.rules`](firestore.rules). Client-side Firestore access is denied; the application accesses Firestore through server-side Admin SDK routes. Seed the sample catalogue from the repository root with:

```powershell
python scripts/seed_firestore.py
```

## Deploy

GitHub stores the source code. Vercel hosts the web app and Python API routes. GitHub Pages by itself cannot run these API handlers.

1. Push the repository to GitHub.
2. Import the GitHub repository into Vercel, using the repository root as the project root.
3. Add `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, `FIREBASE_APP_ID`, and `FIREBASE_SERVICE_ACCOUNT_JSON` in the Vercel project's Environment Variables settings. Keep the Admin SDK credential server-side.
4. Enable Firebase Authentication Email/Password and Firestore. Review and deploy `firestore.rules`.
5. Seed the catalogue with `python scripts/seed_firestore.py` from a machine configured with the Firebase service account.
6. Deploy from Vercel and check the app and API routes at the generated deployment URL.

Vercel can create deployments for pushes to the connected repository and preview deployments for pull requests. Enable Vercel Analytics in the project dashboard if desired; the app includes page-view analytics support and does not send medicine search terms as custom analytics events. Vercel rate limiting can be configured for `/api/v1/compare` and `/api/v1/requests`, subject to plan availability.

## API routes

| Public route | Purpose |
| --- | --- |
| `/api/v1/compare` | Search and compare sample medicine offers |
| `/api/v1/providers` | Return provider options from the catalogue |
| `/api/v1/requests` | Authenticated community request operations |

## Project structure

```text
.
|-- api/                 # Vercel Python API handlers
|-- backend/             # Optional Java / Spring Boot backend
|-- data/                # Bundled sample catalogue and offer CSV files
|-- medisave/            # Shared Python application services
|-- public/              # Frontend HTML, CSS, JavaScript, and assets
|-- scripts/             # Data import and maintenance scripts
|-- dev_server.py        # Local development server
|-- firestore.rules      # Firestore client access policy
|-- vercel.json          # Vercel routes and function configuration
`-- requirements.txt     # Python dependency list
```

## Data and limitations

- `data/medicines.csv`, `pharmacies.csv`, `online_stores.csv`, `prices.csv`, and `online_prices.csv` contain sample data; offers are illustrative and fictional.
- The application does not connect to pharmacy inventory or general review APIs. Provider links open Google search results; MediSave does not collect or summarize those results.
- Medicines absent from the bundled catalogue can be searched on a selected provider site, but do not receive a MediSave comparison until added to the catalogue.
- The symptom phrase matcher is not trained or clinically validated. It provides general information only and should not be used to diagnose or choose treatment.
- Live prices, stock, product details, and reviews require authorized provider or aggregator access. See [Google Custom Search API](https://developers.google.com/custom-search/v1/overview), [Google Merchant reviews API](https://developers.google.com/merchant/api/guides/reviews/products), and [Tata 1mg partnership information](https://www.1mg.com/partnerships) for examples of access requirements.

## License

Distributed under the [MIT License](LICENSE). See the license file for details.
