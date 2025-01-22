import React, { useRef } from 'react';
import useInfiniteScroll from './useInfiniteScroll';
import styles from './DriveContent.module.css';
import { useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faTrash,
  faDownload,
  faPlay,
  faFileArchive,
} from '@fortawesome/free-solid-svg-icons';

export default function InfiniteTable({
  items,
  loadMore,
  hasMore,
  isLoading,
  mediaItems,
  driveLetter,
  handleDelete,
  formatSize,
  openMediaModal, // for example
  buffer = 10, // Number of extra items to keep above/below the visible window
  rowHeight = 50, // Height of a single row (in pixels)
  containerHeight = 600, // Height of the scrollable container
}) {
  // Get the sentinelRef from our custom hook
  const containerRef = useRef(null);
  const sentinelRef = useInfiniteScroll(
    loadMore,
    hasMore,
    containerRef,
    isLoading,
    '500px'
  );
  const navigate = useNavigate();
  // const [startIndex, setStartIndex] = useState(0); // First visible item index
  // const [endIndex, setEndIndex] = useState(0); // Last visible item index

  // const rowsPerViewport = Math.ceil(containerHeight / rowHeight);

  // useEffect(() => {
  //   setEndIndex(rowsPerViewport + buffer); // Set initial visible window
  // }, [rowsPerViewport, buffer]);

  return (
    <div
      ref={containerRef}
      style={{
        height: '100%', // A fixed height container
        overflowY: 'auto', // so we can scroll internally
        // border: "1px solid gray"
      }}
    >
      {/* Table Header: Keep it stationary */}
      <table className={styles.infiniteTable}>
        <colgroup>
          <col style={{ width: '100px' }} /> {/* Thumbnail */}
          <col style={{ width: '200px' }} /> {/* Name */}
          <col style={{ width: '100px' }} /> {/* Size */}
          <col style={{ width: '150px' }} /> {/* Last Modified */}
          <col style={{ width: '200px' }} /> {/* Actions */}
        </colgroup>
        <thead>
          <tr>
            <th style={{ width: '100px' }}>Thumbnail</th>
            <th>Name</th>
            <th>Size</th>
            <th>Last Modified</th>
            <th>Actions</th>
          </tr>
        </thead>
      </table>
      <table className={styles.infiniteTable}>
        <colgroup>
          <col style={{ width: '100px' }} /> {/* Thumbnail */}
          <col style={{ width: '200px' }} /> {/* Name */}
          <col style={{ width: '100px' }} /> {/* Size */}
          <col style={{ width: '150px' }} /> {/* Last Modified */}
          <col style={{ width: '200px' }} /> {/* Actions */}
        </colgroup>
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
                          openMediaModal(mediaIndex); // Open modal for image
                        }
                      }}
                    />
                  </td>
                  <td>{item.name}</td>
                  <td>{item.size ? formatSize(item.size) : '—'}</td>
                  <td>{item.modified}</td>
                  <td>
                    {/* Actions */}

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
                        <a
                          href={`/stream/${driveLetter}/${encodeURIComponent(
                            item.relative_path
                          )}`}
                          className={styles.stream}
                        >
                          <FontAwesomeIcon icon={faPlay} />
                        </a>
                      )}
                      <button
                        className={styles.delete}
                        onClick={() => handleDelete(item)}
                      >
                        <FontAwesomeIcon icon={faTrash} />
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
                </tr>
              );
            }
          })}
        </tbody>
      </table>

      {/* Sentinel DIV: place at the bottom so IntersectionObserver triggers loadMore */}
      {hasMore && !isLoading && (
        <div
          ref={sentinelRef}
          style={{
            height: '1px',
          }}
        />
      )}

      {/* Optional loading indicator */}
      {isLoading && (
        <div style={{ textAlign: 'center', padding: '10px' }}>Loading...</div>
      )}
    </div>
  );
}

// <InfiniteScroll
//       key = {infiniteKey}
//       threshold={100}
//         pageStart={0}
//         loadMore={loadMore}
//         hasMore={hasMore}
//         loader={<div className={styles.loadingSpinner} key="loader">Loading...</div>}
//         useWindow={false}

//         // or useWindow={false} if you want a specific scrollable container
//       >

//       </InfiniteScroll>
