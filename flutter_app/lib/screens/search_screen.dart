import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_downloader/flutter_downloader.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
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
      var status = await Permission.storage.request();
      if (!status.isGranted) {
        _showMessage("Storage permission is required");
        return;
      }

      _showMessage("Fetching download link...");
      final url = await _apiService.getDownloadLink(file.movieId);

      final directory = await getExternalStorageDirectory();
      final downloadsDir = Directory('${directory!.path}/Downloads');
      if (!await downloadsDir.exists()) {
        await downloadsDir.create(recursive: true);
      }

      final taskId = await FlutterDownloader.enqueue(
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("MovieHub Search"),
        centerTitle: true,
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: "Enter movie name...",
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    onSubmitted: (_) => _search(),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: _isLoading ? null : _search,
                  child: const Text("Search"),
                ),
              ],
            ),
          ),
          if (_isLoading) const LinearProgressIndicator(),
          Expanded(
            child: ListView.builder(
              itemCount: _movies.length,
              itemBuilder: (context, index) {
                return MovieCard(
                  movie: _movies[index],
                  onQualityTap: _downloadMovie,
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
