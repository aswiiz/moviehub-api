import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/movie.dart';

class ApiService {
  // Update with your local IP
  static const String baseUrl = 'https://moviehub-api-9qb3.onrender.com';
  static const String omdbApiKey = '9547e152';
  String? _botUsername;

  Future<String> getBotUsername() async {
    if (_botUsername != null) return _botUsername!;
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/info'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _botUsername = data['bot_username'];
        return _botUsername ?? 'greenmoviebot';
      }
    } catch (e) {
      print('Error fetching bot username: $e');
    }
    return 'greenmoviebot';
  }

  Future<List<Movie>> searchMovies(String query) async {
    final cleanQuery = query.trim().toLowerCase();
    try {
      final response = await http.get(Uri.parse('$baseUrl/search?query=${Uri.encodeComponent(cleanQuery)}'));

      if (response.statusCode == 200) {
        List jsonResponse = json.decode(response.body);
        List<Movie> results = jsonResponse
            .map((data) => Movie.fromJson(data))
            .toList();
        
        // Fetch posters and IMDb data in parallel for speed
        await Future.wait(results.map((movie) => fetchImdbData(movie)));
        
        return results;
      } else {
        print('API Error: ${response.statusCode} - ${response.body}');
        throw Exception('Search failed: ${response.body}');
      }
    } catch (e) {
      print('Search request failed: $e');
      rethrow;
    }
  }

  Future<void> fetchImdbData(Movie movie) async {
    if (movie.imdbID == 'tt0000000' || movie.imdbID.startsWith('hub_')) return;
    try {
      final response = await http.get(
          Uri.parse('https://www.omdbapi.com/?i=${movie.imdbID}&apikey=$omdbApiKey'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['Response'] == 'True') {
          movie.posterUrl = data['Poster'] != 'N/A' ? data['Poster'] : null;
          movie.rating = data['imdbRating'] != 'N/A' ? data['imdbRating'] : null;
          movie.genre = data['Genre'] != 'N/A' ? data['Genre'] : null;
          movie.plot = data['Plot'] != 'N/A' ? data['Plot'] : null;
        }
      }
    } catch (e) {
      print('IMDb data error: $e');
    }
  }

  Future<String> getDownloadLink(String movieId) async {
    final response = await http.get(Uri.parse('$baseUrl/get-link?movie_id=$movieId'));

    if (response.statusCode == 200) {
      return json.decode(response.body)['url'];
    } else {
      throw Exception('Failed to get link: ${response.body}');
    }
  }
}
