import React from "react";
import { useParams } from "react-router-dom";
import "./VideoPlayer.css"; // Optional custom styles

function VideoPlayer() {
  const { relative_path } = useParams(); // Ensure this matches route param
  const videoUrl = `/stream/${relative_path}`; // Direct use without double encoding

  const handleVideoError = () => {
    alert("Error loading video. Please try again later.");
  };

  return (
    <div className="video-player">
      <video controls autoPlay width="800" onError={handleVideoError}>
        <source src={videoUrl} type="video/mp4" />
        Your browser does not support the video tag.
      </video>
    </div>
  );
}

export default VideoPlayer;
