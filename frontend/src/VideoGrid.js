import React from "react";
import { Link } from "react-router-dom";
import "./VideoGrid.css"; // Custom styles for the video grid

function VideoGrid({ videos }) {
  return (
    <div className="video-grid">
      {videos.map((video) => (
        <div key={video.file_name} className="video-item">
          <Link to={`/video/${encodeURIComponent(video.relative_path)}`}>
            <img
              src={`/thumbnails/${video.id}.jpg`}
              alt={video.movie_name}
              className="thumbnail"
            />
          </Link>

          <h3>{video.movie_name}</h3>
          <p>Length: {video.length}</p>
        </div>
      ))}
    </div>
  );
}

export default VideoGrid;
