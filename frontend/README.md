IdeaSense AI frontend (Next.js App Router).

## Quick Start
1) Install deps:
```bash
cd frontend
npm install
```
2) Configure API URL:
```bash
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1" > .env.local
```
See `.env.local.example` for more options.
3) Run dev server:
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000).

## Admin Shell
- Admin UI lives under `/admin` and calls `/api/v1/session`.
- Backend must be running (see `backend/README.md`).
- Admin overview dashboard loads live data from `/api/v1/admin-api/overview`.

## API Base URL

The frontend uses `NEXT_PUBLIC_API_BASE_URL` as the single source of truth for API routing:

- When `NEXT_PUBLIC_API_BASE_URL` is non-empty, requests use absolute URLs like `${BASE}/api/v1/...`.
- When `NEXT_PUBLIC_API_BASE_URL` is empty or unset, requests use relative paths like `/api/v1/...` and rely on Next.js rewrites.

For rewrites in that relative mode, set a server-only base URL:

- `BACKEND_INTERNAL_URL` (fallback when `NEXT_PUBLIC_API_BASE_URL` is empty) powers the `/api/v1/:path*` rewrite destination.

## Notes
- You can edit pages under `app/` (auto-reload).
- The design system and tokens live under `styles/`.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
