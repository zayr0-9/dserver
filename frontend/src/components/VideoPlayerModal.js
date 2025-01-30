import React, { useEffect, useRef } from 'react';
import Hls from 'hls.js';
import styles from './VideoPlayerModal.module.css';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faXmark } from '@fortawesome/free-solid-svg-icons';

const VideoPlayerModal = ({ playlistUrl, onClose }) => {
  const videoRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    let hls;

    const initPlayer = () => {
      if (Hls.isSupported()) {
        hls = new Hls();
        hls.loadSource(playlistUrl);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = playlistUrl;
        video.addEventListener('loadedmetadata', () => video.play());
      }
    };

    initPlayer();

    return () => {
      if (hls) {
        hls.destroy();
      }
    };
  }, [playlistUrl]);

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <button className={styles.closeButton} onClick={onClose}>
          <FontAwesomeIcon icon={faXmark} size="2x" />
        </button>
        <video
          ref={videoRef}
          controls
          autoPlay
          className={styles.videoElement}
        />
      </div>
    </div>
  );
};

export default VideoPlayerModal;
