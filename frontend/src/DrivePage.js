import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import styles from "./DrivePage.module.css";

const DrivePage = () => {
  const [drives, setDrives] = useState([]);

  useEffect(() => {
    fetch("/api/drives/")
      .then((response) => response.json())
      .then((data) => setDrives(data.drives))
      .catch((error) => console.error("Error fetching drives:", error));
  }, []);

  return (
    <div className={styles.drives}>
      <div className={styles.body}>
        <h1 className={styles.h1}> Select a Drive to Browse</h1>
        <ul className={styles.ul}>
          {drives.map((drive) => (
            <li className={styles.li} key={drive}>
              <Link to={`/drive/${drive}/`}>{drive}:/</Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default DrivePage;
