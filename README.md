# MediSave India

India-focused medicine discovery demo with sign-in/sign-up, probable spelling matches, generic ingredient lookup, rupee-denominated comparison cards, nearby/online source filters, and a community medicine-request board.

## What works in the bundled demo

- Search common India medicine brands, active ingredients, strengths, and likely misspellings.
- Typed medicine queries use a catalog-fitted TF-IDF retrieval model with word, phrase, and character n-gram features, cosine similarity ranking, and a fuzzy spelling fallback. Explicit strengths are filtered exactly; this is an explainable local NLP model, not a generative or pretrained language model.
- Choose nearby sample pharmacies, online pharmacy listings, or both; use device location to sort nearby listings.
- Compare illustrative INR pack prices and open the provider home pages.
- Search common symptom phrases such as cold and cough, headache, neck pain, sprain, and fever for source-linked self-care information and warning signs.
- Choose a pharmacy website loaded from the catalogue and open a Google site-restricted search for a medicine name.
- For names missing from the sample catalogue, open a provider-scoped Google search or prefill a community request.
- Post and browse community medicine requests after signing in. Local development stores them in SQLite on that computer; deployed requests use Firestore.
- Use the existing dark mode and mobile responsive pages.

The symptom phrase matcher is a small offline prototype, not a trained or clinically validated model. It provides general information only; it does not diagnose or recommend a medicine or dosage. Seek a healthcare professional for personal advice, and call 112 in India for an emergency.

The bundled CSV prices and store offers are fictional demo data, not live quotes or verified stock. The app does not connect to pharmacy inventory or review APIs. Pharmacy-site links open Google search results; MediSave does not collect or summarize those results. An unlisted medicine can be searched manually on the selected provider site, but it will not have a MediSave price comparison until it is added to the catalogue. Live prices, stock, product details, and reviews need authorized provider or aggregator access. Google says its [Custom Search JSON API](https://developers.google.com/custom-search/v1/overview) is closed to new customers; the [Merchant reviews API](https://developers.google.com/merchant/api/guides/reviews/products) is for a merchant's own review feed, not general review search. Tata 1mg lists API integration through its [strategic partnership channel](https://www.1mg.com/partnerships). Confirm prices, pack sizes, stock, and delivery directly with each pharmacy.

## Run locally

From this directory, run `python dev_server.py` (or `python dev_server.py 8787`) and open http://localhost:8787. Search uses the bundled sample catalog without account configuration. Account screens need the four Firebase web settings below. Copy `.env.example` to `.env.local` and fill in your Firebase Web App values and enable the Email/Password provider in Firebase Authentication to enable sign-in and sign-up.

```text
FIREBASE_API_KEY=
FIREBASE_AUTH_DOMAIN=
FIREBASE_PROJECT_ID=
FIREBASE_APP_ID=
```

Community requests on localhost use a SQLite file at `data/local_medisave.sqlite3`, so they survive server restarts on this computer. Deployed requests use the Firebase Admin SDK and Firestore. Add `FIREBASE_SERVICE_ACCOUNT_JSON` to `.env.local` (server-only; never expose it to the browser) and enable Firestore. With the Admin SDK set, the search and provider APIs read the catalogue from Firestore; import the bundled demo catalogue first with `python scripts/seed_firestore.py`. Community posts are written to `medicine_requests`; public catalogue collections are served by the backend while direct client Firestore access stays denied by `firestore.rules`.

## Deploy

Deploy the project to Vercel. Set the four public Firebase web values and the server-only `FIREBASE_SERVICE_ACCOUNT_JSON` in the deployment environment. `api/v1/compare` serves medicine comparisons, `api/v1/providers` serves pharmacy choices from the catalogue, and `api/v1/requests` serves the authenticated community board. Do not commit service-account credentials.

## Vercel analytics and rate limits

The public HTML pages load Vercel Web Analytics on hosted sites through `/_vercel/insights/script.js`. In the Vercel project dashboard, enable **Analytics**, then deploy again. MediSave uses page-view tracking only; it does not send medicine search terms as custom analytics events. See Vercel's [Web Analytics setup](https://vercel.com/docs/analytics/quickstart).

Configure API rate limits in the Vercel project dashboard under **Firewall → Custom Rules**. Add rules for `/api/v1/compare` and `/api/v1/requests`; the Vercel WAF rate-limit rule template starts in log mode, so choose a blocking action after reviewing the logged traffic. Vercel currently lists WAF rate limiting for Pro and Enterprise plans. See [Vercel's rate-limiting guide](https://vercel.com/kb/guide/add-rate-limiting-vercel) and [rate-limit template](https://vercel.com/templates/template/rate-limit-api-requests-firewall-rule).

## Data and styles

- `data/medicines.csv`, `pharmacies.csv`, `online_stores.csv`, `prices.csv`, and `online_prices.csv` contain the sample India catalogue.
- `scripts/seed_firestore.py` imports those CSV rows to Firestore.
- `public/` contains the static pages and prebuilt Tailwind stylesheet. Regenerate Tailwind with `npm i` and `npm run build:css`.
