import React, { useRef, useState, useEffect, useCallback } from 'react';
import useInfiniteScroll from './useInfiniteScroll';
import styles from './DriveContent.module.css';
import { useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import ReactImageGallery from 'react-image-gallery';
import 'react-image-gallery/styles/css/image-gallery.css';
import VideoPlayerModal from './components/VideoPlayerModal';
import axios from 'axios';

// import Lightbox from 'react-spring-lightbox';

// import ArrowButton from './components/ArrowButton';
import {
  faTrash,
  faDownload,
  // faPlay,
  faFileArchive,
  faXmark,
  // faExpand,
  // faCompress,
} from '@fortawesome/free-solid-svg-icons';

// Throttle utility function
const throttle = (func, limit) => {
  let lastFunc;
  let lastRan;
  return function (...args) {
    if (!lastRan) {
      func.apply(this, args);
      lastRan = Date.now();
    } else {
      clearTimeout(lastFunc);
      lastFunc = setTimeout(() => {
        if (Date.now() - lastRan >= limit) {
          func.apply(this, args);
          lastRan = Date.now();
        }
      }, limit - (Date.now() - lastRan));
    }
  };
};

const InfiniteTable = ({
  items,
  loadMore,
  hasMore,
  isLoading,
  mediaItems,
  driveLetter,
  handleDelete,
  formatSize,
  openMediaModal,
  buffer = 50,
  rowHeight = 135,
  containerHeight = 600,
}) => {
  const containerRef = useRef(null);
  const [startIndex, setStartIndex] = useState(0);
  const [endIndex, setEndIndex] = useState(0);
  const navigate = useNavigate();
  const sentinelRef = useInfiniteScroll(
    loadMore,
    hasMore,
    containerRef,
    isLoading,
    '500px'
  );

  //LIGHTBOX
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  // const [showVideoPlayer, setShowVideoPlayer] = useState(false);
  const [currentPlaylistUrl, setCurrentPlaylistUrl] = useState('');
  const handleImageClick = (url) => {
    // iOS Safari workaround - create a hidden anchor tag
    const a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';

    // For iOS, we need to trigger the click in a specific way
    const clickEvent = new MouseEvent('click', {
      view: window,
      bubbles: true,
      cancelable: true,
    });

    a.dispatchEvent(clickEvent);
  };

  const handleConvert = async (e, item) => {
    e.preventDefault();

    try {
      const response = await axios.get('/api/convert-for-stream/', {
        params: {
          path: item.relative_path,
          base_dir: driveLetter,
          quality: 'original', // Default quality
          speed: 'slow', // Default speed
        },
      });

      if (response.data.status === 'success') {
        alert(response.data.message);
      } else {
        alert(response.data.message); // Show error message
      }
    } catch (error) {
      console.error('API call failed:', error);
      alert('An error occurred while processing your request.');
    }
  };
  const galleryItems = items
    .filter((itm) => !itm.is_dir && itm.relative_path && itm.thumbnail)
    .map((itm) => {
      const originalUrl = `/downloads/${driveLetter}/${encodeURIComponent(
        itm.relative_path
      )}`;
      return {
        original: originalUrl, // displayed when the slide is active
        thumbnail: `/transfer/thumbnails/${itm.thumbnail}`, // small image preview (optional)
        thumbnailClass: styles.myThumbnail, // any custom CSS
        // Custom property to check if video
        isVideo: itm.is_video,
        // (Optional) If you want to conditionally render a video:
        renderItem: () => {
          if (itm.is_video) {
            return (
              <video
                src={originalUrl}
                controls
                playsInline
                webkit-playsinline
                muted
                autoPlay
                style={{ maxHeight: 'auto', maxWidth: '100vh' }}
              />
            );
          }
          // Otherwise, display an image
          return (
            <img
              src={originalUrl}
              alt={itm.name || 'Image'}
              style={{ maxHeight: '100vh', maxWidth: 'auto' }}
              onClick={() =>
                handleImageClick(
                  `/downloads/${driveLetter}/${encodeURIComponent(
                    itm.relative_path
                  )}`
                )
              }
            />
          );
        },
      };
    });

  const openGallery = (index) => {
    setCurrentIndex(index);
    setGalleryOpen(true);
  };

  // Close the gallery
  const closeGallery = () => {
    setGalleryOpen(false);
  };
  const handleStreamClick = async (driveLetter, relativePath) => {
    try {
      const encodedPath = encodeURIComponent(relativePath);
      const response = await fetch(
        `/api/stream/${driveLetter}/${encodedPath}/`
      );
      console.log(encodedPath);
      const data = await response.json();

      if (data.playlist_url) {
        setCurrentPlaylistUrl(data.playlist_url);
        // setShowVideoPlayer(true);
      }
    } catch (error) {
      console.error('Streaming error:', error);
    }
  };
  // Calculate visible range
  const calculateRange = useCallback(() => {
    if (!containerRef.current) return;

    const { scrollTop, clientHeight } = containerRef.current;
    const start = Math.max(0, Math.floor(scrollTop / rowHeight) - buffer);
    const end = Math.min(
      items.length,
      start + Math.ceil(clientHeight / rowHeight) + buffer * 2
    );

    return { start, end };
  }, [items.length, buffer, rowHeight]);

  // Scroll handler
  const handleScroll = useCallback(() => {
    // Move throttle inside useCallback to capture dependencies
    const throttledScrollHandler = throttle(() => {
      const range = calculateRange();
      if (range) {
        setStartIndex(range.start);
        setEndIndex(range.end);
      }

      if (containerRef.current) {
        const { scrollTop, clientHeight, scrollHeight } = containerRef.current;
        if (
          scrollTop + clientHeight >= scrollHeight - 500 &&
          !isLoading &&
          hasMore
        ) {
          loadMore();
        }
      }
    }, 50);

    return throttledScrollHandler;
  }, [calculateRange, isLoading, hasMore, loadMore, containerRef]); // Explicit dependencies

  // Initial setup and resize handler
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScrollWithThrottle = handleScroll();

    // Initial calculation
    const range = calculateRange();
    if (range) {
      setStartIndex(range.start);
      setEndIndex(range.end);
    }

    // Add event listeners
    container.addEventListener('scroll', handleScrollWithThrottle);
    window.addEventListener('resize', handleScrollWithThrottle);

    return () => {
      container.removeEventListener('scroll', handleScrollWithThrottle);
      window.removeEventListener('resize', handleScrollWithThrottle);
    };
  }, [handleScroll, calculateRange]);

  // Reset range when items change
  useEffect(() => {
    const range = calculateRange();
    if (range) {
      setStartIndex(range.start);
      setEndIndex(range.end);
    }
  }, [items, calculateRange]);

  const visibleItems = items.slice(startIndex, endIndex);
  const totalHeight = items.length * rowHeight;
  // const sentinelPosition = endIndex * rowHeight;

  return (
    <div
      ref={containerRef}
      style={{
        height: '93vh',
        overflowY: 'auto',
        position: 'relative',
      }}
    >
      {/* Virtualized table structure */}
      <table className={styles.infiniteTable}>
        <colgroup>
          <col style={{ width: '100px' }} />
          <col style={{ width: '200px' }} />
          <col style={{ width: '100px' }} />
          <col style={{ width: '150px' }} />
          <col style={{ width: '200px' }} />
        </colgroup>
        <thead style={{ display: 'table' }}>
          <tr>
            <th style={{ width: '100px' }}>Thumbnail</th>
            <th style={{ width: '200px' }}>Name</th>
            <th style={{ width: '100px' }}>Size</th>
            <th style={{ width: '150px' }}>Last Modified</th>
            <th style={{ width: '200px' }}>Actions</th>
          </tr>
        </thead>
      </table>

      <div style={{ height: totalHeight }}>
        <table className={styles.infiniteTable}>
          <colgroup>
            <col style={{ width: '100px' }} />
            <col style={{ width: '200px' }} />
            <col style={{ width: '100px' }} />
            <col style={{ width: '150px' }} />
            <col style={{ width: '200px' }} />
          </colgroup>
          <tbody
            style={{ transform: `translateY(${startIndex * rowHeight}px)` }}
            key={items.length}
          >
            {visibleItems.map((item, index) => {
              const actualIndex = startIndex + index;

              // Decide which class to use based on whether actualIndex is even or odd
              const rowClass =
                actualIndex % 2 === 0 ? styles.rowEven : styles.rowOdd;
              return (
                <TableRow
                  key={item.relative_path}
                  item={item}
                  driveLetter={driveLetter}
                  mediaItems={mediaItems}
                  formatSize={formatSize}
                  handleDelete={handleDelete}
                  openMediaModal={openMediaModal}
                  navigate={navigate}
                  rowHeight={rowHeight}
                  galleryItems={galleryItems}
                  openGallery={openGallery}
                  className={rowClass}
                  handleStreamClick={handleStreamClick}
                  handleConvert={handleConvert}
                />
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Loading sentinel */}
      {hasMore && (
        <div
          ref={sentinelRef}
          style={{
            position: 'absolute',
            top: `${totalHeight}px`,
            height: '1px',
          }}
        />
      )}

      {isLoading && (
        <div style={{ textAlign: 'center', padding: '10px' }}>Loading...</div>
      )}
      {galleryOpen && (
        <div className={styles.overlay}>
          {/* <button onClick={closeGallery} className={styles.closeButton}>
            <FontAwesomeIcon icon={faXmark} size="2x" />
          </button> */}
          <button onClick={closeGallery} className={styles.fullscreenButton}>
            <FontAwesomeIcon icon={faXmark} size="2x" />
          </button>
          <ReactImageGallery
            items={galleryItems}
            // The starting slide
            startIndex={currentIndex}
            // Called BEFORE switching to the next slide
            onBeforeSlide={() => {
              // Pause the current slide’s video (if any)
              const videos = document.querySelectorAll(
                '.myGalleryOverlay video'
              );
              videos.forEach((video) => {
                if (!video.paused) {
                  video.pause();
                }
              });
            }}
            // Called AFTER switching to the new slide
            onSlide={(newSlideIndex) => {
              setCurrentIndex(newSlideIndex);
              if (
                newSlideIndex === galleryItems.length - 10 &&
                hasMore &&
                !isLoading
              ) {
                loadMore();
              }
              // Attempt to autoplay the new slide’s video
              const videos = document.querySelectorAll(
                '.myGalleryOverlay .image-gallery-slide .active video'
              );
              // Usually there's at most one <video> in the newly active slide
              if (videos.length > 0) {
                const video = videos[0];
                // Attempt to play automatically
                video.play().catch((err) => {
                  console.log(
                    'Video autoplay failed, user gesture required on some mobile devices.',
                    err
                  );
                });
              }
            }}
            showPlayButton={false}
            showThumbnails={false}
            showIndex={true}
            disableThumbnailScroll={false}
            disableThumbnailSwipe={false}
            showFullscreenButton={false}
            additionalClass="myGalleryOverlay"
            showNav={window.innerWidth >= 768}
            renderLeftNav={(onClick, disabled) => (
              <button
                type="button"
                className={`${styles.customNav} ${styles.customLeftNav}`}
                disabled={disabled}
                onClick={onClick}
              ></button>
            )}
            renderRightNav={(onClick, disabled) => (
              <button
                type="button"
                className={`${styles.customNav} ${styles.customRightNav}`}
                disabled={disabled}
                onClick={onClick}
              ></button>
            )}
          />

          {currentPlaylistUrl && (
            <VideoPlayerModal
              playlistUrl={currentPlaylistUrl}
              onClose={() => setCurrentPlaylistUrl(null)}
            />
          )}
        </div>
      )}
      {/* )} */}
    </div>
  );
};

// Memoized row component
const TableRow = React.memo(
  ({
    item,
    driveLetter,
    mediaItems,
    formatSize,
    handleDelete,
    openMediaModal,
    navigate,
    rowHeight,
    galleryItems,
    openGallery,
    className,
    handleStreamClick,
    handleConvert,
  }) => {
    // console.log(mediaItems);
    const getGalleryIndex = () => {
      // Build the same "originalUrl" used in galleryItems
      const originalUrl = `/downloads/${driveLetter}/${encodeURIComponent(
        item.relative_path
      )}`;

      return galleryItems.findIndex((g) => g.original === originalUrl);
    };
    return (
      <tr style={{ height: `${rowHeight}px` }} className={className}>
        {item.is_dir ? (
          // Folder row
          <>
            <td>
              <span role="img" aria-label="Folder" style={{ fontSize: '2em' }}>
                📁
              </span>
            </td>
            <td>
              <button
                className={styles.linkButton}
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
              </button>
            </td>
            <td>{item.size ? formatSize(item.size) : '—'}</td>
            <td>{item.modified}</td>
            <td>
              <div className={styles.actionButtons}>
                <a
                  href={`/download_zip/?path=${encodeURIComponent(
                    item.relative_path.replace(/\\/g, '/')
                  )}&base_dir=${driveLetter}`}
                  className={styles.download}
                >
                  <FontAwesomeIcon
                    icon={faDownload}
                    style={{ marginRight: '10px' }}
                  />
                  <FontAwesomeIcon icon={faFileArchive} />
                </a>
                <button
                  className={styles.delete}
                  onClick={() => handleDelete(item)}
                >
                  <FontAwesomeIcon icon={faTrash} />
                </button>
              </div>
            </td>
          </>
        ) : item.thumbnail ? (
          // Thumbnail file row
          <>
            <td>
              <img
                src={`/transfer/thumbnails/${item.thumbnail}`}
                alt="Thumbnail"
                className={styles.thumbnail}
                onClick={() => {
                  const index = getGalleryIndex();
                  console.log('Index found:', index);
                  if (index !== -1) {
                    openGallery(index);
                  }
                }}
              />
            </td>
            <td>{item.name}</td>
            <td>{item.size ? formatSize(item.size) : '—'}</td>
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
                  <FontAwesomeIcon icon={faDownload} />
                </a>
                {item.is_video && (
                  <div className={styles.actionButtons}>
                    <button
                      className={styles.convert}
                      onClick={(e) => handleConvert(e, item)}
                    >
                      Convert
                    </button>
                  </div>
                )}
                <button
                  className={styles.delete}
                  onClick={() => handleDelete(item)}
                >
                  <FontAwesomeIcon icon={faTrash} />
                </button>
              </div>
            </td>
          </>
        ) : (
          // Regular file row
          <>
            <td>
              <span role="img" aria-label="File" style={{ fontSize: '2em' }}>
                📄
              </span>
            </td>
            <td>
              {item.is_text ? (
                <div className={styles.text}>
                  <button
                    className={styles.linkButton}
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
                  </button>
                </div>
              ) : (
                item.name
              )}
            </td>
            <td>{item.size ? formatSize(item.size) : '—'}</td>
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
                  <FontAwesomeIcon icon={faDownload} />
                </a>
                <button
                  className={styles.delete}
                  onClick={() => handleDelete(item)}
                >
                  <FontAwesomeIcon icon={faTrash} />
                </button>
              </div>
            </td>
          </>
        )}
      </tr>
    );
  }
);

export default InfiniteTable;
