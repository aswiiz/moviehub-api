# MovieHub - Full Stack Movie Search & Downloader

A full-stack application consisting of a FastAPI backend (converted from Telegram bot logic) and a Flutter mobile app.

## Project Structure
- `backend/`: FastAPI server with search and link generation services.
- `flutter_app/`: Flutter mobile application with Material UI.

---

## 🚀 Backend Setup (Python FastAPI)

### 1. Requirements
- Python 3.9+
- MongoDB instance (running locally or in cloud)

### 2. Installation
```bash
cd backend
pip install -r requirements.txt
```

### 3. Configuration
Edit the `.env` file in the `backend/` directory:
- `MONGO_URI`: Your MongoDB connection string.
- `OMDB_API_KEY`: Your OMDb API key (for movie posters).
- `FILE_TO_LINK_API`: URL of your FileToLink backend instance.
- `API_PORT`: Default is 8000.

### 4. Running the Server
```bash
python app.py
```
The API will be available at `http://0.0.0.0:8000`.

---

## 📱 Flutter App Setup

### 1. Requirements
- Flutter SDK (latest stable)
- Android Studio / VS Code with Flutter extension

### 2. Configuration
Open `lib/services/api_service.dart` and update the `baseUrl` to your local machine's IP address:
```dart
static const String baseUrl = 'http://192.168.X.X:8000';
```

### 3. Installation
```bash
cd flutter_app
# Initialize the project structure if not already present
flutter create .
flutter pub get
```

### 4. Running the App
```bash
flutter run
```

---

## 🛠 Building the APK

### Debug APK
```bash
flutter build apk --debug
```
Output: `build/app/outputs/flutter-apk/app-debug.apk`

### Release APK
```bash
flutter build apk --release
```
Output: `build/app/outputs/flutter-apk/app-release.apk`

---

## 📝 Features & Logic
- **Search Logic**: Extracted from `blackcatoffical` Telegram bot patterns. It performs regex-based searches on the file collection in MongoDB.
- **Link Logic**: Integrates with `FileToLink` backend to convert internal IDs to direct download links.
- **Posters**: Fetched dynamically via OMDb API using `imdbID` provided by the backend.
- **Downloader**: Uses `flutter_downloader` to handle background downloads on Android.

---

## ⚠️ Important Note for Android
To allow downloads and network access:
1. Ensure your `AndroidManifest.xml` has:
   - `<uses-permission android:name="android.permission.INTERNET"/>`
   - `<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>`
2. Configure `provider` for `flutter_downloader` as per its official documentation if you encounter issues.
