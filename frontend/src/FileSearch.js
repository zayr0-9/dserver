// FileSearch.js
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import styles from "./FileSearch.module.css";

function getParentPath(relativePath) {
  // Convert any backslashes to forward slashes
  let path = relativePath.replace(/\\/g, "/");

  // Remove trailing slash just in case
  path = path.replace(/\/+$/, "");

  console.log(path);
  const parts = path.split("/");
  console.log(parts);

  if (parts.length > 1) {
    parts.pop(); // remove the filename portion
    return parts.join("/");
  } else {
    // If the file is in the root folder, parent path is empty
    return "";
  }
}

const FileSearch = ({ driveLetter = "D" }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [results, setResults] = useState([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const navigate = useNavigate();

  const handleSearch = async () => {
    try {
      const response = await axios.get(
        `/api/search/?q=${encodeURIComponent(searchTerm)}`,
        { withCredentials: true }
      );
      setResults(response.data.results || []);
      setIsDropdownOpen(true);
    } catch (error) {
      console.error("Search error:", error);
      setResults([]);
      setIsDropdownOpen(false);
    }
  };

  const toggleDropdown = () => {
    setIsDropdownOpen((prev) => !prev);
  };

  const handleResultClick = (item) => {
    // If it's a directory, navigate to that directory
    if (item.is_dir) {
      navigate(
        `/drive/${driveLetter}/${encodeURIComponent(item.relative_path)}`
      );
    } else {
      // If it's a file, navigate to the parent directory (DriveContents),
      // optionally highlight or do something else
      const parentPath = getParentPath(item.relative_path);
      console.log(item.relative_path);
      // Add a highlight query param if you want to highlight the file in DriveContents
      // Otherwise, just navigate to the parent
      navigate(
        `/drive/${driveLetter}/${encodeURIComponent(
          parentPath
        )}?highlight=${encodeURIComponent(item.name)}`
      );
    }
    // Optionally, close the dropdown after navigating
    setIsDropdownOpen(false);
  };

  const handleViewFile = (item) => {
    // Suppose you only allow "edit" for text files. If you track that with item.is_text
    // Navigate to your /edit route
    navigate(`/edit/${driveLetter}/${encodeURIComponent(item.relative_path)}`);
    setIsDropdownOpen(false);
  };

  return (
    <div className={styles.searchBarContainer}>
      <input
        type="text"
        placeholder="Search files..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSearch();
        }}
      />
      <button onClick={handleSearch}>Search</button>

      {/* Dropdown results */}
      {isDropdownOpen && results.length > 0 && (
        <div className={styles.searchResults}>
          <button onClick={toggleDropdown} className={styles.hideButton}>
            Hide
          </button>

          {results.map((item) => (
            <div key={item.relative_path} className={styles.searchResultItem}>
              {/* 
                If it's a directory, clicking name opens it in DriveContents.
                If it's a file, clicking name navigates to parent directory but highlights file. 
              */}
              <span
                className={styles.searchResultName}
                onClick={() => handleResultClick(item)}
                style={{ cursor: "pointer" }}
              >
                <strong>{item.name}</strong>
                {item.is_dir ? " (Directory)" : ""}
              </span>

              {/* If it's not a directory, show additional actions */}
              {!item.is_dir && (
                <div className={styles.searchResultActions}>
                  {/* Download */}
                  <a
                    href={`/downloads/${driveLetter}/${encodeURIComponent(
                      item.relative_path
                    )}`}
                    download
                    className={styles.downloadLink}
                  >
                    Download
                  </a>

                  {/* View/Edit Button (e.g., for text files) */}
                  {item.is_text && (
                    <button
                      onClick={() => handleViewFile(item)}
                      className={styles.viewButton}
                    >
                      View
                    </button>
                  )}
                  {/* Similarly, if item.is_video => add a Stream button, etc. */}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileSearch;
