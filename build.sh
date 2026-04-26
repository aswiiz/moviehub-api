#!/bin/bash
# Use existing flutter if available to save time/resources
if command -v flutter &> /dev/null; then
  echo "Using system flutter"
elif [ -d "/home/raswin/development/flutter/bin" ]; then
  export PATH="$PATH:/home/raswin/development/flutter/bin"
  echo "Using development flutter"
elif [ -d "flutter" ]; then
  export PATH="$PATH:`pwd`/flutter/bin"
  echo "Using local flutter"
else
  echo "Cloning Flutter SDK..."
  git clone https://github.com/flutter/flutter.git -b stable --depth 1
  export PATH="$PATH:`pwd`/flutter/bin"
fi

flutter config --enable-web
cd flutter_app
flutter pub get
flutter build web --release
