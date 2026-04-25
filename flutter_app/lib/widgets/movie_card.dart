import 'package:flutter/material.dart';
import '../models/movie.dart';

class MovieCard extends StatelessWidget {
  final Movie movie;
  final Function(MovieFile) onQualityTap;
  final bool isLoading;

  const MovieCard({
    super.key,
    required this.movie,
    required this.onQualityTap,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
            child: movie.posterUrl != null
                ? Image.network(
                    movie.posterUrl!,
                    height: 200,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) =>
                        Container(height: 200, color: Colors.grey[300], child: const Icon(Icons.movie, size: 50)),
                  )
                : Container(height: 200, color: Colors.grey[300], child: const Icon(Icons.movie, size: 50)),
          ),
          Padding(
            padding: const EdgeInsets.all(12.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  movie.title,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                const Text("Available Qualities:", style: TextStyle(color: Colors.grey)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: movie.files.map((file) {
                    return ActionChip(
                      label: Text("${file.quality} (${file.size})"),
                      onPressed: isLoading ? null : () => onQualityTap(file),
                      backgroundColor: Colors.blueAccent.withOpacity(0.1),
                      labelStyle: const TextStyle(color: Colors.blueAccent),
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
