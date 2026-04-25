import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/movie.dart';

class ApiService {
  // Update with your local IP
  static const String baseUrl = 'https://moviehub-api-9qb3.onrender.com';
  static const String omdbApiKey = '9547e152';

  Future<List<Movie>> searchMovies(String query) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/search?query=${Uri.encodeComponent(query)}'));

      if (response.statusCode == 200) {
        List jsonResponse = json.decode(response.body);
        List<Movie> results = jsonResponse
            .map((data) => Movie.fromJson(data))
            .toList();
        
        // Fetch posters in parallel for speed
        await Future.wait(results.map((movie) async {
          movie.posterUrl = await fetchPoster(movie.imdbID);
        }));
        
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

  Future<String?> fetchPoster(String imdbID) async {
    if (imdbID == 'tt0000000') return null;
    try {
      final response = await http.get(
          Uri.parse('https://www.omdbapi.com/?i=$imdbID&apikey=$omdbApiKey'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['Poster'] != 'N/A' ? data['Poster'] : null;
      }
    } catch (e) {
      print('Poster error: $e');
    }
    return null;
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
