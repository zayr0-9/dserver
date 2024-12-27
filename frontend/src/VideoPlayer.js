// VideoPlayer.js

import React, { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import { useParams } from "react-router-dom";
import axios from "axios";

const VideoPlayer = () => {
  const { driveLetter, "*": pathParam } = useParams();
  const videoRef = useRef(null);
  const [playlistUrl, setPlaylistUrl] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const videoPath = encodeURIComponent(pathParam || "");

  useEffect(() => {
    // Fetch playlist URL and other data from the backend
    axios
      .get(`/api/stream/${driveLetter}/${videoPath}/`)
      .then((response) => {
        const data = response.data;
        setPlaylistUrl(data.playlist_url);
      })
      .catch((error) => {
        setErrorMessage("Error fetching video stream");
        console.error(error);
      });
  }, [driveLetter, videoPath]);

  useEffect(() => {
    if (playlistUrl && videoRef.current) {
      const videoElement = videoRef.current;
      if (Hls.isSupported()) {
        const hls = new Hls();
        hls.loadSource(playlistUrl);
        hls.attachMedia(videoElement);
        hls.on(Hls.Events.MANIFEST_PARSED, function () {
          videoElement.play();
        });
      } else if (videoElement.canPlayType("application/vnd.apple.mpegurl")) {
        // For Safari browsers
        videoElement.src = playlistUrl;
        videoElement.addEventListener("loadedmetadata", function () {
          videoElement.play();
        });
      } else {
        setErrorMessage("This browser does not support HLS");
      }
    }
  }, [playlistUrl]);

  if (errorMessage) {
    return <div>{errorMessage}</div>;
  }

  return (
    <div className="video-player-container">
      <video
        ref={videoRef}
        controls
        style={{ width: "100%", height: "auto" }}
      ></video>
    </div>
  );
};

export default VideoPlayer;
