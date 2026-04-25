# Deployment Instructions

This project is configured for deployment on **Render** (Backend) and **Vercel** (Frontend).

## 1. Backend Deployment (Render)

1.  **Connect Repository**: Go to [Render Dashboard](https://dashboard.render.com/) and create a new **Web Service**.
2.  **Configuration**: Render should automatically detect the `render.yaml` file. If not:
    *   **Runtime**: `Python`
    *   **Build Command**: `pip install -r backend/requirements.txt`
    *   **Start Command**: `cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT`
3.  **Environment Variables**: Ensure you set the following in the Render Dashboard:
    *   `MONGO_URI`
    *   `OMDB_API_KEY`
    *   `BOT_TOKEN`
    *   `ADMIN_ID`
    *   `API_ID`
    *   `API_HASH`

## 2. Frontend Deployment (Vercel)

The Flutter app is now configured for Web support.

### Option A: Manual Build & Deploy (Recommended)
1.  **Build locally**:
    ```bash
    cd flutter_app
    flutter build web --release
    ```
2.  **Deploy**:
    *   Install Vercel CLI: `npm install -g vercel`
    *   Run `vercel` inside the `flutter_app/build/web` directory.

### Option B: Automated (GitHub/GitLab)
1.  Push your code to GitHub.
2.  In Vercel, create a new project and select the repository.
3.  Set the **Root Directory** to `flutter_app`.
4.  **IMPORTANT**: Since Vercel doesn't have Flutter pre-installed, you might need a custom build script or use a GitHub Action to build and then deploy to Vercel.

## 3. Connecting Frontend to Backend
*   The API URL is currently set in `flutter_app/lib/services/api_service.dart`.
*   Ensure `baseUrl` matches your Render service URL (e.g., `https://moviehub-api.onrender.com`).
