import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_downloader/flutter_downloader.dart';
import 'screens/search_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  if (!kIsWeb) {
    await FlutterDownloader.initialize(
      debug: true,
      ignoreSsl: true,
    );
  }

  runApp(const MovieHubApp());
}

class MovieHubApp extends StatelessWidget {
  const MovieHubApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MovieHub',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const SearchScreen(),
    );
  }
}
