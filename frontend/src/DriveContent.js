// DriveContents.js

import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import queryString from "query-string";
import "./DriveContent.css";

const DriveContents = () => {
  const { driveLetter, "*": pathParam } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // Parse the current path from the URL
  const currentPath = pathParam || "";

  // Parse query parameters from the URL
  const queryParams = queryString.parse(location.search);

  // State variables
  const [items, setItems] = useState([]);
  const [baseDir, setBaseDir] = useState("");
  const [thumbnailSize, setThumbnailSize] = useState(
    queryParams.thumbnail_size || "100"
  );
  const [isPrivate, setIsPrivate] = useState(false);
  const [pin, setPin] = useState("");
  const [pinError, setPinError] = useState("");
  const [errorMessage, setErrorMessage] = useState(""); // For displaying fetch errors

  // Sorting and filtering state
  const [sorting, setSorting] = useState({
    sort_by: queryParams.sort_by || "name",
    sort_dir: queryParams.sort_dir || "asc",
  });

  const [filtering, setFiltering] = useState({
    filter_type: queryParams.filter_type || "all",
    file_type: queryParams.file_type || "all",
    size_min: queryParams.size_min || "",
    size_max: queryParams.size_max || "",
    date_from: queryParams.date_from || "",
    date_to: queryParams.date_to || "",
  });

  // Media Modal State
  const [mediaModalOpen, setMediaModalOpen] = useState(false);
  const [mediaItems, setMediaItems] = useState([]);
  const [currentMediaIndex, setCurrentMediaIndex] = useState(0);

  // Loading States
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmittingPin, setIsSubmittingPin] = useState(false);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [driveLetter, currentPath, sorting, filtering, thumbnailSize]);

  const fetchData = () => {
    setIsLoading(true); // Start loading
    setErrorMessage(""); // Reset previous errors

    const params = {
      path: currentPath || "",
      sort_by: sorting.sort_by,
      sort_dir: sorting.sort_dir,
      type: filtering.filter_type,
      file_type: filtering.file_type,
      size_min: filtering.size_min,
      size_max: filtering.size_max,
      date_from: filtering.date_from,
      date_to: filtering.date_to,
      thumbnail_size: thumbnailSize,
    };

    const query = queryString.stringify(params);

    fetch(`/api/drive/${driveLetter}/files/?${query}`, {
      credentials: "include", // Include cookies for session-based authentication
    })
      .then((response) => {
        if (response.status === 401) {
          // Directory is private and requires PIN
          return response.json().then((data) => {
            if (data.is_private) {
              setIsPrivate(true);
              setItems([]);
              setBaseDir(driveLetter);
              setIsLoading(false);
              return;
            }
            throw new Error("Unauthorized");
          });
        }
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        if (!isPrivate && data) {
          setItems(data.items);
          setBaseDir(data.base_dir);
          setThumbnailSize(data.thumbnail_size.toString());
        }
        setIsLoading(false); // End loading
      })
      .catch((error) => {
        console.error("Error fetching drive contents:", error);
        setErrorMessage("Failed to load drive contents. Please try again.");
        setIsLoading(false); // End loading
      });
  };

  const handleSortingChange = (e) => {
    setSorting({
      ...sorting,
      [e.target.name]: e.target.value,
    });
  };

  const handleFilteringChange = (e) => {
    setFiltering({
      ...filtering,
      [e.target.name]: e.target.value,
    });
  };

  const handleThumbnailSizeChange = (e) => {
    setThumbnailSize(e.target.value);
  };

  const handleSortingSubmit = (e) => {
    e.preventDefault();
    const params = {
      ...queryParams,
      sort_by: sorting.sort_by,
      sort_dir: sorting.sort_dir,
    };
    const newQuery = queryString.stringify(params);
    navigate(`${location.pathname}?${newQuery}`);
  };

  const handleFilteringSubmit = (e) => {
    e.preventDefault();
    const params = {
      ...queryParams,
      ...filtering,
    };
    const newQuery = queryString.stringify(params);
    navigate(`${location.pathname}?${newQuery}`);
  };

  const handleThumbnailSizeSubmit = (e) => {
    e.preventDefault();
    const params = {
      ...queryParams,
      thumbnail_size: thumbnailSize,
    };
    const newQuery = queryString.stringify(params);
    navigate(`${location.pathname}?${newQuery}`);
  };

  // Handle Media Modal interactions
  const openMediaModal = (mediaIndex) => {
    if (mediaIndex >= 0 && mediaIndex < mediaItems.length) {
      setCurrentMediaIndex(mediaIndex);
      setMediaModalOpen(true);
    }
  };

  const closeMediaModal = () => {
    setMediaModalOpen(false);
  };

  const nextMedia = () => {
    setCurrentMediaIndex((prevIndex) => (prevIndex + 1) % mediaItems.length);
  };

  const prevMedia = () => {
    setCurrentMediaIndex(
      (prevIndex) => (prevIndex - 1 + mediaItems.length) % mediaItems.length
    );
  };

  // Helper function to format bytes to human-readable form
  const formatSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Prepare media items for modal
  useEffect(() => {
    const mediaFiles = items
      .filter((item) => !item.is_dir && item.thumbnail)
      .map((item) => ({
        type: item.is_video ? "video" : "image",
        src: `/downloads/${driveLetter}/${encodeURIComponent(
          item.relative_path
        )}`,
        thumbnail: `/thumbnails/${item.thumbnail}`,
        name: item.name,
        downloadUrl: `/downloads/${driveLetter}/${encodeURIComponent(
          item.relative_path
        )}`,
      }));
    setMediaItems(mediaFiles);
  }, [items, driveLetter]);

  // Handle PIN Submission
  const handlePinSubmit = (e) => {
    e.preventDefault();

    setIsSubmittingPin(true);
    setPinError(""); // Reset previous errors

    const data = {
      path: currentPath || "",
      pin: pin,
    };

    fetch(`/api/drive/${driveLetter}/validate_pin/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "include", // Include cookies for session
      body: JSON.stringify(data),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          setIsPrivate(false);
          setPin("");
          setPinError("");
          fetchData(); // Re-fetch data after successful PIN validation
        } else {
          setPinError(data.error || "Incorrect PIN. Please try again.");
        }
        setIsSubmittingPin(false);
      })
      .catch((error) => {
        console.error("Error submitting PIN:", error);
        setPinError("An error occurred. Please try again.");
        setIsSubmittingPin(false);
      });
  };

  return (
    <div className="drive-contents">
      {/* Top Bar */}
      <div className="top-bar">
        <h1>
          File Transfer - {driveLetter}:\{currentPath}
        </h1>
        <button className="option" onClick={() => navigate("/drive/")}>
          Home
        </button>
      </div>

      {/* Forms Section */}
      <div className="form-section">
        {/* Sorting Form */}
        <form onSubmit={handleSortingSubmit} id="sortingForm">
          <label htmlFor="sort_by">Sort by:</label>
          <select
            name="sort_by"
            id="sort_by"
            value={sorting.sort_by}
            onChange={handleSortingChange}
          >
            <option value="name">Name</option>
            <option value="size">Size</option>
            <option value="modified">Last Modified</option>
            <option value="created">Creation Date</option>
          </select>

          <label htmlFor="sort_dir">Order:</label>
          <select
            name="sort_dir"
            id="sort_dir"
            value={sorting.sort_dir}
            onChange={handleSortingChange}
          >
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>

          <button type="submit">Apply</button>
        </form>

        {/* Filtering Form */}
        <form onSubmit={handleFilteringSubmit} id="filteringForm">
          <label htmlFor="filter_type">Type:</label>
          <select
            name="filter_type"
            id="filter_type"
            value={filtering.filter_type}
            onChange={handleFilteringChange}
          >
            <option value="all">All</option>
            <option value="dir">Directories</option>
            <option value="file">Files</option>
          </select>

          <label htmlFor="file_type">File Type:</label>
          <select
            name="file_type"
            id="file_type"
            value={filtering.file_type}
            onChange={handleFilteringChange}
          >
            <option value="all">All</option>
            <option value="images">Images</option>
            <option value="videos">Videos</option>
            <option value="documents">Documents</option>
            <option value="audio">Audio</option>
            <option value="archives">Archives</option>
          </select>

          <label htmlFor="size_min">Size Min (bytes):</label>
          <input
            type="number"
            name="size_min"
            id="size_min"
            value={filtering.size_min}
            onChange={handleFilteringChange}
            style={{ width: "100px" }}
          />

          <label htmlFor="size_max">Size Max (bytes):</label>
          <input
            type="number"
            name="size_max"
            id="size_max"
            value={filtering.size_max}
            onChange={handleFilteringChange}
            style={{ width: "100px" }}
          />

          <label htmlFor="date_from">Date From:</label>
          <input
            type="date"
            name="date_from"
            id="date_from"
            value={filtering.date_from}
            onChange={handleFilteringChange}
          />

          <label htmlFor="date_to">Date To:</label>
          <input
            type="date"
            name="date_to"
            id="date_to"
            value={filtering.date_to}
            onChange={handleFilteringChange}
          />

          <button type="submit">Apply Filters</button>
        </form>

        {/* Thumbnail Size Form */}
        {/* <form onSubmit={handleThumbnailSizeSubmit}>
          <label htmlFor="thumbnail_size">Thumbnail Size:</label>
          <select
            name="thumbnail_size"
            id="thumbnail_size"
            value={thumbnailSize}
            onChange={handleThumbnailSizeChange}
          >
            <option value="100">100x100</option>
            <option value="300">300x300</option>
            <option value="500">500x500</option>
            <option value="1000">1000x1000</option>
            <option value="2000">2000x2000</option>
          </select>
          <button type="submit">Apply</button>
        </form> */}
      </div>

      {/* Display Error Message */}
      {errorMessage && (
        <div className="error-message">
          <p style={{ color: "red" }}>{errorMessage}</p>
        </div>
      )}

      {/* Loading Indicator */}
      {isLoading && <div className="loading-spinner">Loading...</div>}

      {/* File Table */}
      <h2>Available Files and Directories</h2>
      <table>
        <colgroup>
          <col style={{ width: "100px" }} /> {/* Thumbnail */}
          <col style={{ width: "100px" }} /> {/* Name */}
          <col style={{ width: "30px" }} /> {/* Size */}
          <col style={{ width: "50px" }} /> {/* Last Modified */}
          <col style={{ width: "100px" }} /> {/* Actions */}
        </colgroup>
        <thead>
          <tr>
            <th>Thumbnail</th>
            <th>Name</th>
            <th>Size</th>
            <th>Last Modified</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => {
            if (item.is_dir) {
              return (
                <tr key={item.relative_path}>
                  <td>
                    <span role="img" aria-label="Folder">
                      📁
                    </span>
                  </td>
                  <td>
                    <a
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        navigate(
                          `/drive/${driveLetter}/${encodeURIComponent(
                            item.relative_path
                          )}`
                        );
                      }}
                    >
                      {item.name}
                    </a>
                  </td>
                  <td>{item.size_formatted}</td>
                  <td>{item.modified}</td>
                  <td>
                    <div className="action-buttons">
                      <a
                        href={`/download_zip/?path=${encodeURIComponent(
                          item.relative_path
                        )}&base_dir=${driveLetter}`}
                        className="download"
                      >
                        Download Zip
                      </a>
                    </div>
                  </td>
                </tr>
              );
            } else if (item.thumbnail) {
              // Find the mediaItems index for this item
              const mediaIndex = mediaItems.findIndex(
                (mediaItem) =>
                  mediaItem.src ===
                  `/downloads/${driveLetter}/${encodeURIComponent(
                    item.relative_path
                  )}`
              );

              return (
                <tr key={item.relative_path}>
                  <td>
                    <img
                      src={`/transfer/thumbnails/${item.thumbnail}`}
                      alt="Thumbnail"
                      className="thumbnail"
                      onClick={() => {
                        if (mediaIndex !== -1) {
                          openMediaModal(mediaIndex);
                        }
                      }}
                    />
                  </td>
                  <td>{item.name}</td>
                  <td>{item.size ? formatSize(item.size) : "—"}</td>
                  <td>{item.modified}</td>
                  <td>
                    <div className="action-buttons">
                      <a
                        href={`/downloads/${driveLetter}/${encodeURIComponent(
                          item.relative_path
                        )}`}
                        download
                        className="download"
                      >
                        Download
                      </a>
                      {item.is_video && (
                        <a
                          href={`/stream/${driveLetter}/${encodeURIComponent(
                            item.relative_path
                          )}`}
                          className="stream"
                        >
                          Stream
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              );
            } else {
              // Non-thumbnail files
              return (
                <tr key={item.relative_path}>
                  <td>
                    <span role="img" aria-label="File">
                      📄
                    </span>
                  </td>
                  <td>{item.name}</td>
                  <td>{item.size ? formatSize(item.size) : "—"}</td>
                  <td>{item.modified}</td>
                  <td>
                    <div className="action-buttons">
                      <a
                        href={`/downloads/${driveLetter}/${encodeURIComponent(
                          item.relative_path
                        )}`}
                        download
                        className="download"
                      >
                        Download
                      </a>
                      {item.is_video && (
                        <a
                          href={`/stream/${driveLetter}/${encodeURIComponent(
                            item.relative_path
                          )}`}
                          className="stream"
                        >
                          Stream
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              );
            }
          })}
        </tbody>
      </table>

      {/* Media Modal */}
      {mediaModalOpen &&
        mediaItems.length > 0 &&
        mediaItems[currentMediaIndex] && (
          <div className="modal" id="mediaModal">
            {/* Close Button */}
            <a href="#" className="close-modal" onClick={closeMediaModal}>
              &times;
            </a>

            {/* Previous Button */}
            <button className="prev-btn" onClick={prevMedia}>
              &#10094;
            </button>

            {/* Modal Content */}
            <div className="modal-content">
              <div className="modal-media-container">
                {mediaItems[currentMediaIndex].type === "image" ? (
                  <img
                    src={mediaItems[currentMediaIndex].src}
                    alt="Image"
                    className="modal-media"
                  />
                ) : (
                  <video
                    src={mediaItems[currentMediaIndex].src}
                    controls
                    autoPlay
                    className="modal-media"
                  />
                )}
              </div>
              <div className="action-buttons">
                <a
                  href={mediaItems[currentMediaIndex].downloadUrl}
                  download
                  className="download"
                >
                  Download
                </a>
              </div>
            </div>

            {/* Next Button */}
            <button className="next-btn" onClick={nextMedia}>
              &#10095;
            </button>
          </div>
        )}

      {/* PIN Modal */}
      {isPrivate && (
        <div className="modal active" id="pinModal">
          <div className="modal-content">
            <h2>Enter Admin PIN to Access Directory</h2>
            <form onSubmit={handlePinSubmit} id="pinForm">
              <input
                type="password"
                name="pin"
                placeholder="Enter Admin PIN"
                required
                value={pin}
                onChange={(e) => setPin(e.target.value)}
              />
              <button type="submit" disabled={isSubmittingPin}>
                {isSubmittingPin ? "Submitting..." : "Submit"}
              </button>
            </form>
            {pinError && (
              <p id="pinError" style={{ color: "red" }}>
                {pinError}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DriveContents;
