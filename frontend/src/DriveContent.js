// DriveContents.js

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import queryString from 'query-string';
import styles from './DriveContent.module.css';
import SearchBar from './FileSearch'; // Import your SearchBar here
import InfiniteTable from './InfiniteTable'; // our new custom component
import axios from 'axios';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowUp, faHome, faUpload } from '@fortawesome/free-solid-svg-icons';

function getParentPath(path) {
  // Convert backslashes to forward slashes
  let normalized = path.replace(/\\/g, '/');
  // Remove trailing slash
  normalized = normalized.replace(/\/+$/, '');
  // Split
  const parts = normalized.split('/');
  if (parts.length > 1) {
    parts.pop();
    return parts.join('/');
  }
  return ''; // means root
}

const DriveContents = () => {
  const { driveLetter, '*': pathParam } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // Parse the current path from the URL
  const currentPath = pathParam || '';

  // Parse query parameters from the URL
  const queryParams = queryString.parse(location.search);
  const [allItems, setAllItems] = useState([]);
  // State variables
  const [items, setItems] = useState([]);
  const [baseDir, setBaseDir] = useState('');
  const [thumbnailSize, setThumbnailSize] = useState(
    queryParams.thumbnail_size || '100'
  );
  const [isPrivate, setIsPrivate] = useState(false);
  const [pin, setPin] = useState('');
  const [pinError, setPinError] = useState('');
  const [errorMessage, setErrorMessage] = useState(''); // For displaying fetch errors
  const [isDropdownVisible, setIsDropdownVisible] = useState(false);
  const dropdownRef = useRef(null);
  const isRoot = currentPath === '';
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
    document.addEventListener('mousedown', handleClickOutside);

    // Cleanup the event listener when the component is unmounted
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Sorting and filtering state
  const [sorting, setSorting] = useState({
    sort_by: queryParams.sort_by || 'name',
    sort_dir: queryParams.sort_dir || 'asc',
  });

  const [filtering, setFiltering] = useState({
    filter_type: queryParams.filter_type || 'all',
    file_type: queryParams.file_type || 'all',
    size_min: queryParams.size_min || '',
    size_max: queryParams.size_max || '',
    date_from: queryParams.date_from || '',
    date_to: queryParams.date_to || '',
  });

  // Pagination state
  const [pagination, setPagination] = useState({
    current_page: 0,
    page_size: parseInt(queryParams.page_size) || 300, // smaller page_size works better for infinite scroll
    total_items: 0,
  });
  //for infinite scroll
  const [hasMore, setHasMore] = useState(true); // For InfiniteScroll
  const [isFetching, setIsFetching] = useState(false);
  const [navigationInProgress, setNavigationInProgress] = useState(false);

  // Media Modal State
  const [mediaModalOpen, setMediaModalOpen] = useState(false);
  const [mediaItems, setMediaItems] = useState([]);
  const [currentMediaIndex, setCurrentMediaIndex] = useState(0);

  // Loading States
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmittingPin, setIsSubmittingPin] = useState(false);
  // Suppose we track a page number in our state
  const [page, setPage] = useState(1);
  const pageSize = 20; // or whatever

  useEffect(() => {
    // setAllItems([]);
    if (page > 1 || allItems.length === 0) {
      loadMore(page);
    }
    setHasMore(true);
    // fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  useEffect(() => {
    setPage(1);
    setAllItems([]);
    setHasMore(true);
    setIsLoading(false);
    setNavigationInProgress(true);
    loadMore(1);
    console.log(currentPath, page);
  }, [location.pathname, driveLetter, currentPath]);

  const loadMore = async (thePage) => {
    console.log('navprog true', navigationInProgress, isFetching, hasMore);
    // if (isFetching || isPrivate || !hasMore) return;
    console.log(
      `[${Date.now()}}] loadMore => page:`,
      thePage,
      navigationInProgress
    );

    setIsFetching(true);

    const params = {
      path: currentPath || '',
      sort_by: sorting.sort_by,
      sort_dir: sorting.sort_dir,
      type: filtering.filter_type,
      file_type: filtering.file_type,
      size_min: filtering.size_min,
      size_max: filtering.size_max,
      date_from: filtering.date_from,
      date_to: filtering.date_to,
      page_size: pageSize,
      page: thePage, //  pass the page from infinite scroller
      thumbnail_size: queryParams.thumbnail_size || '100',
    };

    try {
      const query = queryString.stringify(params);
      const response = await fetch(
        `/api/drive/${driveLetter}/files/?${query}`,
        {
          credentials: 'include',
        }
      );

      if (response.status === 401) {
        // handle private
        const data = await response.json();
        if (data.is_private) {
          setIsPrivate(true);
          setIsFetching(false);
          setHasMore(false); // Can't load more
          return;
        }
        throw new Error('Unauthorized');
      }

      if (!response.ok) {
        throw new Error('Failed to fetch items');
      }

      const data = await response.json();
      // data.items is the chunk for THIS page

      // If there are new items, add them to allItems
      setAllItems((prevItems) => [...prevItems, ...data.items]);

      if (data.items.length < pageSize) {
        setHasMore(false);
      }

      // Check if we can load more
      const totalFetchedSoFar =
        (thePage - 1) * pagination.page_size + data.items.length;
      const stillHasMore = totalFetchedSoFar < data.pagination.total_items;

      setPagination({
        current_page: data.pagination.current_page,
        page_size: data.pagination.page_size,
        total_items: data.pagination.total_items,
      });
      // setHasMore(stillHasMore);
    } catch (error) {
      console.error('Error fetching data:', error);
      // Maybe set an error message in your state
      setHasMore(false);
    } finally {
      setIsFetching(false);
    }

    setNavigationInProgress(false);
    console.log('navprog false', navigationInProgress);
  };

  const nextPage = () => {
    console.log('nextPage', navigationInProgress);
    if (!isFetching && hasMore && !navigationInProgress) {
      console.log('is Fetching');
      console.log(isFetching);
      setPage((prev) => prev + 1);
    }
  };

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
  // const handlePageChange = (pageNumber) => {
  //   const params = {
  //     ...queryParams,
  //     page: pageNumber,
  //   };
  //   const newQuery = queryString.stringify(params);
  //   navigate(`${location.pathname}?${newQuery}`);
  // };

  // const handleNextPage = () => {
  //   if (pagination.current_page < pagination.total_pages) {
  //     handlePageChange(pagination.current_page + 1);
  //   }
  // };

  // const handlePrevPage = () => {
  //   if (pagination.current_page > 1) {
  //     handlePageChange(pagination.current_page - 1);
  //   }
  // };

  // Handle specific page number click
  // const handlePageNumberClick = (pageNumber) => {
  //   handlePageChange(pageNumber);
  // };

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
        .post('/api/delete/', data, {
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
          },
          withCredentials: true,
        })
        .then((response) => {
          if (response.data.success) {
            // loadMore();
          } else {
            alert(response.data.error || 'Failed to delete the item');
          }
        })
        .catch((error) => {
          console.error('Error deleting item: ', error);
          alert('An error occurred while deleting the item');
        });
    }
  };

  // Helper function to format bytes to human-readable form
  const formatSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Prepare media items for modal
  useEffect(() => {
    const mediaFiles = items
      .filter((item) => !item.is_dir && item.thumbnail)
      .map((item) => ({
        type: item.is_video ? 'video' : 'image',
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
  }, [items, driveLetter, page, currentPath]);

  // Handle PIN Submission
  const handlePinSubmit = (e) => {
    e.preventDefault();

    setIsSubmittingPin(true);
    setPinError(''); // Reset previous errors

    const data = {
      path: currentPath || '',
      pin: pin,
    };

    fetch(`/api/drive/${driveLetter}/validate_pin/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'include', // Include cookies for session
      body: JSON.stringify(data),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          setIsPrivate(false);
          setPin('');
          setPinError('');
          // loadMore(); // Re-fetch data after successful PIN validation
        } else {
          setPinError(data.error || 'Incorrect PIN. Please try again.');
        }
        setIsSubmittingPin(false);
      })
      .catch((error) => {
        console.error('Error submitting PIN:', error);
        setPinError('An error occurred. Please try again.');
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
          <button className={styles.option} onClick={() => navigate('/drive/')}>
            <FontAwesomeIcon icon={faHome} />
          </button>
          <button
            className={styles.option}
            onClick={handleGoUp}
            disabled={isRoot}
          >
            <FontAwesomeIcon icon={faArrowUp} />
          </button>

          {/* "Upload Files" Link */}
          {/* <Link
              to={`/upload?base_dir=${encodeURIComponent(
                baseDir
              )}&path=${encodeURIComponent(currentPath)}`}
              className={styles.uploadLink}
            >
              Upload Files
            </Link> */}
          <button
            className={styles.option}
            onClick={() =>
              navigate(
                `/upload?base_dir=${encodeURIComponent(
                  baseDir
                )}&path=${encodeURIComponent(currentPath)}`
              )
            }
          >
            <FontAwesomeIcon icon={faUpload} />
          </button>
        </div>
        {/* Advanced Filters Dropdown */}
        <div className={styles.secondRow}>
          <div className={styles.searchBar}>
            <SearchBar />
          </div>
          <div className={styles.advancedFilters}>
            <button
              className={styles.advancedFiltersButton}
              onClick={toggleDropdown}
            >
              Filters
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
      </div>

      {/* Display Error Message */}
      {errorMessage && (
        <div className={styles.errorMessage}>
          <p style={{ color: 'red' }}>{errorMessage}</p>
        </div>
      )}

      {/* Loading Indicator */}
      {isLoading && <div className={styles.loadingSpinner}>Loading...</div>}

      {/* File Table */}
      <h2>Available Files and Directories</h2>

      <InfiniteTable
        items={allItems}
        loadMore={nextPage}
        hasMore={hasMore}
        isLoading={isFetching}
        mediaItems={mediaItems}
        driveLetter={driveLetter}
        handleDelete={handleDelete}
        formatSize={formatSize}
        openMediaModal={openMediaModal}
      />

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
                {mediaItems[currentMediaIndex].type === 'image' ? (
                  <img
                    src={mediaItems[currentMediaIndex].src}
                    alt="image"
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
                className={styles.delete}
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
                {isSubmittingPin ? 'Submitting...' : 'Submit'}
              </button>
            </form>
            {pinError && (
              <p id="pinError" style={{ color: 'red' }}>
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
