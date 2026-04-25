class MovieFile {
  final String quality;
  final String size;
  final String movieId;

  MovieFile({
    required this.quality,
    required this.size,
    required this.movieId,
  });

  factory MovieFile.fromJson(Map<String, dynamic> json) {
    return MovieFile(
      quality: json['quality'],
      size: json['size'],
      movieId: json['movie_id'],
    );
  }
}

class Movie {
  final String title;
  final String imdbID;
  final List<MovieFile> files;
  String? posterUrl;

  Movie({
    required this.title,
    required this.imdbID,
    required this.files,
    this.posterUrl,
  });

  factory Movie.fromJson(Map<String, dynamic> json) {
    return Movie(
      title: json['title'],
      imdbID: json['imdbID'],
      files: (json['files'] as List)
          .map((f) => MovieFile.fromJson(f))
          .toList(),
    );
  }
}
