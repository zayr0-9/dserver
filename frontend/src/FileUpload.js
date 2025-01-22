// FileUpload.js

import React, { useState, useEffect, useRef } from 'react';
// import "./FileUpload.css";
import io from 'socket.io-client';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';

const FileUpload = () => {
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const baseDir = queryParams.get('base_dir') || 'C'; // Default to "C" if not provided
  const rawPath = queryParams.get('path') || ''; // Default to "" if not provided

  // Sanitize currentPath by removing leading and trailing slashes
  const currentPath = rawPath.replace(/^\/+|\/+$/g, '');
  const navigate = useNavigate();
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState(0);
  const [totalFiles, setTotalFiles] = useState(0);
  const [totalBytes, setTotalBytes] = useState(0);
  const [uploadedBytes, setUploadedBytes] = useState(0);
  const [progressPercentage, setProgressPercentage] = useState(0);
  const [notification, setNotification] = useState('');

  const uploadedFilesRef = useRef(0);
  const totalFilesRef = useRef(0);
  const totalBytesRef = useRef(0);
  const uploadedBytesRef = useRef(0);

  // Initialize Socket.IO client
  const socket = io('http://192.168.0.82'); // Update to your Socket.IO server URL

  useEffect(() => {
    // Listen for notifications from the Node.js server
    socket.on('notification', (message) => {
      alert(message); // Display the success message to the user
      setNotification(message);
    });

    // Listen for file upload progress (optional)
    socket.on('progress', (data) => {
      console.log(`Upload progress: ${data.percentage}%`);
      // You can integrate this with your progress bar if needed
    });

    // Cleanup on unmount
    return () => {
      socket.disconnect();
    };
  }, [socket]);

  // Utility function to get CSRF token from cookies
  const getCSRFToken = () => {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';').map((cookie) => cookie.trim());
    for (let cookie of cookies) {
      if (cookie.startsWith(name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return '';
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    const maxSize = 1000 * 1024 * 1024; // 100 MB

    // Client-side file size validation
    for (let i = 0; i < files.length; i++) {
      if (files[i].size > maxSize) {
        alert(`File ${files[i].name} exceeds the maximum size of 100 MB.`);
        return;
      }
    }

    setSelectedFiles(files);
  };

  const startUpload = async (event) => {
    event.preventDefault(); // Prevent form submission

    const files = document.getElementById('fileInput').files;

    // Reset refs
    uploadedFilesRef.current = 0;
    uploadedBytesRef.current = 0;

    // Calculate total bytes
    let totalBytes = 0;
    for (let i = 0; i < files.length; i++) {
      totalBytes += files[i].size;
    }
    totalBytesRef.current = totalBytes;
    totalFilesRef.current = files.length;

    // Reset state
    setTotalFiles(files.length);
    setTotalBytes(totalBytes);
    setUploadedFiles(0);
    setUploadedBytes(0);
    setProgressPercentage(0);
    setNotification('');

    if (files.length > 0) {
      document.getElementById('progressContainer').style.display = 'block';
      document.getElementById(
        'progressText'
      ).textContent = `Uploading 0 of ${files.length} files`;

      uploadFiles(files); // Start the upload process
    }
  };

  const uploadFiles = (files) => {
    setUploading(true);

    const fileUploadProgress = new Array(files.length).fill(0);

    Array.from(files).forEach((file, index) => {
      const formData = new FormData();
      formData.append('files', file);

      const url = currentPath
        ? `/api/upload/${baseDir}/${encodeURIComponent(currentPath)}/`
        : `/api/upload/${baseDir}/`;

      axios
        .post(url, formData, {
          headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'multipart/form-data',
          },
          withCredentials: true,
          onUploadProgress: (progressEvent) => {
            const { loaded } = progressEvent;

            // Update the progress for this file
            fileUploadProgress[index] = loaded;

            // Sum up total uploaded bytes
            const uploadedBytes = fileUploadProgress.reduce((a, b) => a + b, 0);
            uploadedBytesRef.current = uploadedBytes;
            setUploadedBytes(uploadedBytes);

            // Update the progress bar
            const overallProgress =
              (uploadedBytes / totalBytesRef.current) * 100;

            const progressBar = document.getElementById('progressBarInner');
            const progressText = document.getElementById('progressText');
            progressBar.style.width = `${overallProgress}%`;
            progressText.textContent = `Uploading ${
              uploadedFilesRef.current
            } of ${totalFilesRef.current} files (${Math.round(
              overallProgress
            )}%)`;
          },
        })
        .then((response) => {
          // Update uploaded files count
          uploadedFilesRef.current += 1;
          setUploadedFiles(uploadedFilesRef.current);

          // Ensure that the progress for this file is set to its total size
          fileUploadProgress[index] = file.size;

          // Check if all files are uploaded
          if (uploadedFilesRef.current === totalFilesRef.current) {
            closeProgressBar();
            setUploading(false);
          }
        })
        .catch((error) => {
          alert(
            `Error uploading ${file.name}: ${
              error.response?.data?.error || error.message
            }`
          );
          setUploading(false);
        });
    });
  };

  const closeProgressBar = () => {
    document.getElementById('progressContainer').style.display = 'none';
    document.getElementById('progressText').textContent = 'Upload complete!';
  };

  return (
    <div className="file-upload-container">
      <h1>Upload Files</h1>
      <form method="POST" encType="multipart/form-data" onSubmit={startUpload}>
        <input
          type="file"
          id="fileInput"
          name="files"
          multiple
          onChange={handleFileChange}
        />
        <button type="submit" disabled={uploading}>
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>
      <a
        href="#"
        onClick={(e) => {
          e.preventDefault();
          navigate(`/drive/${baseDir}/${encodeURIComponent(rawPath)}`);
        }}
      >
        View Upload{' '}
      </a>
      {/* Example link, adjust as needed */}
      {/* Progress bar */}
      <div
        className="progress-bar"
        id="progressContainer"
        style={{ display: 'none' }}
      >
        <div id="progressBarInner" className="progress-bar-inner"></div>
      </div>
      <p id="progressText"></p>
      {notification && <p className="notification">{notification}</p>}
    </div>
  );
};

export default FileUpload;
