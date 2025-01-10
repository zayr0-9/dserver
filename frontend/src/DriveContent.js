// DriveContents.js

import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate, useLocation, Link } from "react-router-dom";
import queryString from "query-string";
import styles from "./DriveContent.module.css";
import SearchBar from "./FileSearch"; // Import your SearchBar here

import axios from "axios";

function getParentPath(path) {
  // Convert backslashes to forward slashes
  let normalized = path.replace(/\\/g, "/");
  // Remove trailing slash
  normalized = normalized.replace(/\/+$/, "");
  // Split
  const parts = normalized.split("/");
  if (parts.length > 1) {
    parts.pop();
    return parts.join("/");
  }
  return ""; // means root
}

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
  const [isDropdownVisible, setIsDropdownVisible] = useState(false);
  const dropdownRef = useRef(null);
  const isRoot = currentPath === "";
  const toggleDropdown = () => {
    setIsDropdownVisible(!isDropdownVisible);
  };
  const handleGoUp = () => {
    const parentPath = getParentPath(currentPath);
    navigate(`/drive/${driveLetter}/${encodeURIComponent(parentPath)}`);
  };
  // Close the dropdown when clicking outside of it
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownVisible(false); // Hide dropdown when clicking outside
      }
    };

    // Add event listener to document
    document.addEventListener("mousedown", handleClickOutside);

    // Cleanup the event listener when the component is unmounted
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

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

  // Pagination state
  const [pagination, setPagination] = useState({
    current_page: parseInt(queryParams.page) || 1,
    page_size: parseInt(queryParams.page_size) || 100,
    total_pages: 1,
    total_items: 0,
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
  }, [
    driveLetter,
    currentPath,
    sorting,
    filtering,
    thumbnailSize,
    pagination.current_page,
    pagination.page_size,
    isPrivate,
  ]);

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
      page: pagination.current_page,
      page_size: pagination.page_size,
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
          setPagination({
            current_page: data.pagination.current_page,
            page_size: data.pagination.page_size,
            total_pages: data.pagination.total_pages,
            total_items: data.pagination.total_items,
          });
        }
        setIsLoading(false); // End loading
      })
      .catch((error) => {
        console.error("Error fetching drive contents:", error);
        setErrorMessage("Failed to load drive contents. Please try again.");
        setIsLoading(false); // End loading
      });
  };

  // Utility function to get CSRF token from cookies
  const getCSRFToken = () => {
    const name = "csrftoken";
    const cookies = document.cookie.split(";").map((cookie) => cookie.trim());
    for (let cookie of cookies) {
      if (cookie.startsWith(name + "=")) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return "";
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
      page: 1, // Reset to first page on sort
    };
    const newQuery = queryString.stringify(params);
    navigate(`${location.pathname}?${newQuery}`);
  };

  const handleFilteringSubmit = (e) => {
    e.preventDefault();
    const params = {
      ...queryParams,
      ...filtering,
      page: 1, // Reset to first page on filter
    };
    const newQuery = queryString.stringify(params);
    navigate(`${location.pathname}?${newQuery}`);
  };

  const handleThumbnailSizeSubmit = (e) => {
    e.preventDefault();
    const params = {
      ...queryParams,
      thumbnail_size: thumbnailSize,
      page: 1, // Reset to first page on thumbnail size change
    };
    const newQuery = queryString.stringify(params);
    navigate(`${location.pathname}?${newQuery}`);
  };

  // Handle Pagination
  const handlePageChange = (pageNumber) => {
    const params = {
      ...queryParams,
      page: pageNumber,
    };
    const newQuery = queryString.stringify(params);
    navigate(`${location.pathname}?${newQuery}`);
  };

  const handleNextPage = () => {
    if (pagination.current_page < pagination.total_pages) {
      handlePageChange(pagination.current_page + 1);
    }
  };

  const handlePrevPage = () => {
    if (pagination.current_page > 1) {
      handlePageChange(pagination.current_page - 1);
    }
  };

  // Handle specific page number click
  const handlePageNumberClick = (pageNumber) => {
    handlePageChange(pageNumber);
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

  const handleDelete = (item) => {
    if (window.confirm(`Are you sure you want to delete ${item.name}?`)) {
      const data = {
        base_dir: driveLetter,
        relative_path: item.relative_path,
      };

      axios
        .post("/api/delete/", data, {
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
          },
          withCredentials: true,
        })
        .then((response) => {
          if (response.data.success) {
            fetchData();
          } else {
            alert(response.data.error || "Failed to delete the item");
          }
        })
        .catch((error) => {
          console.error("Error deleting item: ", error);
          alert("An error occurred while deleting the item");
        });
    }
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
        thumbnail: `/transfer/thumbnails/${item.thumbnail}`,
        itemRef: item,
        name: item.name,
        downloadUrl: `/downloads/${driveLetter}/${encodeURIComponent(
          item.relative_path
        )}`,
      }));
    setMediaItems(mediaFiles);
  }, [items, driveLetter, pagination]);

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
    <div className={styles.driveContents}>
      {/* Top Bar */}
      <div className={styles.topBar}>
        <div className={styles.topRow}>
          <h1 className={styles.h1}>
            File Transfer - {driveLetter}:\{currentPath}
          </h1>
          <button className={styles.option} onClick={() => navigate("/drive/")}>
            Home
          </button>
          <button
            className={styles.option}
            onClick={handleGoUp}
            disabled={isRoot}
          >
            Go Up
          </button>
          {/* "Upload More Files" Link */}
          <div className={styles.uploadLink}>
            <Link
              to={`/upload?base_dir=${encodeURIComponent(
                baseDir
              )}&path=${encodeURIComponent(currentPath)}`}
              className={styles.uploadLink}
            >
              Upload More Files
            </Link>
          </div>
          {/* Advanced Filters Dropdown */}
          <div className={styles.advancedFilters}>
            <button
              className={styles.advancedFiltersButton}
              onClick={toggleDropdown}
            >
              Advanced Filters
            </button>

            {isDropdownVisible && (
              <div className={styles.dropdown} ref={dropdownRef}>
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
                    min="0"
                  />

                  <label htmlFor="size_max">Size Max (bytes):</label>
                  <input
                    type="number"
                    name="size_max"
                    id="size_max"
                    value={filtering.size_max}
                    onChange={handleFilteringChange}
                    min="0"
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
              </div>
            )}
          </div>
        </div>
        <div className={styles.searchBar}>
          <SearchBar />
        </div>
      </div>

      {/* Display Error Message */}
      {errorMessage && (
        <div className={styles.errorMessage}>
          <p style={{ color: "red" }}>{errorMessage}</p>
        </div>
      )}

      {/* Loading Indicator */}
      {isLoading && <div className={styles.loadingSpinner}>Loading...</div>}

      {/* File Table */}
      <h2>Available Files and Directories</h2>
      <table>
        <colgroup>
          <col style={{ width: "100px" }} /> {/* Thumbnail */}
          <col style={{ width: "200px" }} /> {/* Name */}
          <col style={{ width: "100px" }} /> {/* Size */}
          <col style={{ width: "150px" }} /> {/* Last Modified */}
          <col style={{ width: "200px" }} /> {/* Actions */}
        </colgroup>
        <thead>
          <tr>
            <th style={{ width: "100px" }}>Thumbnail</th>
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
                  <td>{item.size ? formatSize(item.size) : "—"}</td>
                  <td>{item.modified}</td>
                  <td>
                    <div className={styles.actionButtons}>
                      <a
                        href={`/download_zip/?path=${encodeURIComponent(
                          item.relative_path.replace(/\\/g, "/")
                        )}&base_dir=${driveLetter}`}
                        className={styles.download}
                      >
                        Download Zip
                      </a>
                      <button
                        className={styles.deleteButton}
                        onClick={() => handleDelete(item)}
                      >
                        Delete
                      </button>
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
                      className={styles.thumbnail}
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
                    <div className={styles.actionButtons}>
                      <a
                        href={`/downloads/${driveLetter}/${encodeURIComponent(
                          item.relative_path
                        )}`}
                        download
                        className={styles.download}
                      >
                        Download
                      </a>
                      {item.is_video && (
                        <button
                          className={styles.streamButton}
                          onClick={() => {
                            navigate(
                              `/video-player/${driveLetter}/${encodeURIComponent(
                                item.relative_path
                              )}`
                            );
                          }}
                        >
                          Stream
                        </button>
                      )}
                      <button
                        className={styles.deleteButton}
                        onClick={() => handleDelete(item)}
                      >
                        Delete
                      </button>
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
                  <td>
                    {item.is_text ? (
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          navigate(
                            `/edit/${driveLetter}/${encodeURIComponent(
                              item.relative_path
                            )}`
                          );
                        }}
                      >
                        {item.name}
                      </a>
                    ) : (
                      item.name
                    )}
                  </td>
                  <td>{item.size ? formatSize(item.size) : "—"}</td>
                  <td>{item.modified}</td>
                  <td>
                    <div className={styles.actionButtons}>
                      <a
                        href={`/downloads/${driveLetter}/${encodeURIComponent(
                          item.relative_path
                        )}`}
                        download
                        className={styles.download}
                      >
                        Download
                      </a>
                      {item.is_video && (
                        <a
                          href={`/stream/${driveLetter}/${encodeURIComponent(
                            item.relative_path
                          )}`}
                          className={styles.stream}
                        >
                          Stream
                        </a>
                      )}
                      <button
                        className={styles.deleteButton}
                        onClick={() => handleDelete(item)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              );
            }
          })}
        </tbody>
      </table>

      {/* Pagination Controls */}
      <div className={styles.pagination}>
        <button
          onClick={handlePrevPage}
          disabled={pagination.current_page === 1}
          className={styles.paginationButton}
        >
          &laquo; Prev
        </button>

        <button
          onClick={handleNextPage}
          disabled={pagination.current_page === pagination.total_pages}
          className={styles.paginationButton}
        >
          Next &raquo;
        </button>
      </div>

      {/* Media Modal */}
      {mediaModalOpen &&
        mediaItems.length > 0 &&
        mediaItems[currentMediaIndex] && (
          <div className={styles.modal} id="mediaModal">
            {/* Close Button */}
            <span className={styles.closeModal} onClick={closeMediaModal}>
              &times;
            </span>

            {/* Previous Button */}
            <button className={styles.prevBtn} onClick={prevMedia}>
              &#10094;
            </button>

            {/* Modal Content */}
            <div className={styles.modalContent}>
              <div className={styles.modalMediaContainer}>
                {mediaItems[currentMediaIndex].type === "image" ? (
                  <img
                    src={mediaItems[currentMediaIndex].src}
                    alt="Image"
                    className={styles.modalMedia}
                  />
                ) : (
                  <video
                    src={mediaItems[currentMediaIndex].src}
                    controls
                    autoPlay
                    className={styles.modalMedia}
                  />
                )}
              </div>
            </div>
            <div className={styles.actionButtons}>
              <a
                href={mediaItems[currentMediaIndex].downloadUrl}
                download
                className={styles.download}
              >
                Download
              </a>
              <button
                className={styles.deleteButton}
                onClick={() =>
                  handleDelete(mediaItems[currentMediaIndex].itemRef)
                }
              >
                Delete
              </button>
            </div>

            {/* Next Button */}
            <button className={styles.nextBtn} onClick={nextMedia}>
              &#10095;
            </button>
          </div>
        )}

      {/* PIN Modal */}
      {isPrivate && (
        <div className={styles.modal} id="pinModal">
          <div className={styles.modalContent}>
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
