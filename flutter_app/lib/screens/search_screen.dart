import 'dart:io' show Directory;
import 'dart:ui';
import 'package:animate_do/animate_do.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_downloader/flutter_downloader.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/movie.dart';
import '../services/api_service.dart';
import '../widgets/movie_card.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final ApiService _apiService = ApiService();
  final TextEditingController _searchController = TextEditingController();
  List<Movie> _movies = [];
  bool _isLoading = false;

  Future<void> _search() async {
    if (_searchController.text.isEmpty) return;

    setState(() {
      _isLoading = true;
      _movies = [];
    });

    try {
      final results = await _apiService.searchMovies(_searchController.text);
      setState(() {
        _movies = results;
        if (_movies.isEmpty) {
          _showMessage("No results found");
        }
      });
    } catch (e) {
      _showMessage("Search failed: $e");
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _downloadMovie(MovieFile file) async {
    try {
      _showMessage("Fetching download link...");
      final url = await _apiService.getDownloadLink(file.movieId);

      if (kIsWeb) {
        final uri = Uri.parse(url);
        if (await canalLaunch(uri)) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        } else {
          _showMessage("Could not launch $url");
        }
        return;
      }

      var status = await Permission.storage.request();
      if (!status.isGranted) {
        _showMessage("Storage permission is required");
        return;
      }

      final directory = await getExternalStorageDirectory();
      final downloadsDir = Directory('${directory!.path}/Downloads');
      if (!await downloadsDir.exists()) {
        await downloadsDir.create(recursive: true);
      }

      await FlutterDownloader.enqueue(
        url: url,
        savedDir: downloadsDir.path,
        showNotification: true,
        openFileFromNotification: true,
        saveInPublicStorage: true,
      );

      _showMessage("Download started!");
    } catch (e) {
      _showMessage("Download failed: $e");
    }
  }

  // Helper for web launch check (since canLaunch can be tricky on web)
  Future<bool> canalLaunch(Uri uri) async {
    return await canLaunchUrl(uri);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: FadeInDown(child: const Text("MovieHub", style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2, color: Colors.white))),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Stack(
        children: [
          // Dark Gradient Background
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFF0F2027), Color(0xFF203A43), Color(0xFF2C5364)],
              ),
            ),
          ),
          
          SafeArea(
            child: Column(
              children: [
                // Glassmorphism Search Bar
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: FadeIn(
                    duration: const Duration(milliseconds: 800),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(20),
                      child: BackdropFilter(
                        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: Colors.white.withOpacity(0.2)),
                          ),
                          child: Row(
                            children: [
                              Expanded(
                                child: TextField(
                                  controller: _searchController,
                                  style: const TextStyle(color: Colors.white),
                                  decoration: const InputDecoration(
                                    hintText: "Search for movies...",
                                    hintStyle: TextStyle(color: Colors.white70),
                                    border: InputBorder.none,
                                  ),
                                  onSubmitted: (_) => _search(),
                                ),
                              ),
                              IconButton(
                                icon: const Icon(Icons.search, color: Colors.white),
                                onPressed: _isLoading ? null : _search,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                
                if (_isLoading) 
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: LinearProgressIndicator(backgroundColor: Colors.transparent, color: Colors.blueAccent),
                  ),
                  
                Expanded(
                  child: _movies.isEmpty && !_isLoading
                      ? Center(
                          child: FadeInUp(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.movie_filter, size: 80, color: Colors.white.withOpacity(0.3)),
                                const SizedBox(height: 16),
                                Text("Discover your next favorite movie", style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 16)),
                              ],
                            ),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.only(top: 8, bottom: 20),
                          itemCount: _movies.length,
                          itemBuilder: (context, index) {
                            return FadeInUp(
                              delay: Duration(milliseconds: index * 100),
                              child: MovieCard(
                                movie: _movies[index],
                                onQualityTap: _downloadMovie,
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
