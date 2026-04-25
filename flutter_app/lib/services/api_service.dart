import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/movie.dart';

class ApiService {
  // Update with your local IP
  static const String baseUrl = 'http://192.168.1.100:8000';
  static const String omdbApiKey = 'YOUR_OMDB_API_KEY';

  Future<List<Movie>> searchMovies(String query) async {
    final response = await http.get(Uri.parse('$baseUrl/search?query=$query'));

    if (response.statusCode == 200) {
      List jsonResponse = json.decode(response.body);
      List<Movie> results = jsonResponse
          .map((data) => Movie.fromJson(data))
          .toList();
      
      // Fetch posters for each movie using OMDb API
      for (var movie in results) {
        movie.posterUrl = await fetchPoster(movie.imdbID);
      }
      
      return results;
    } else {
      throw Exception('Search failed: ${response.body}');
    }
  }

  Future<String?> fetchPoster(String imdbID) async {
    if (imdbID == 'tt0000000') return null;
    try {
      final response = await http.get(
          Uri.parse('http://www.omdbapi.com/?i=$imdbID&apikey=$omdbApiKey'));
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
