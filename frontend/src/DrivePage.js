import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
// import "./DrivePage.css";

const DrivePage = () => {
  const [drives, setDrives] = useState([]);

  useEffect(() => {
    fetch("/api/drives/")
      .then((response) => response.json())
      .then((data) => setDrives(data.drives))
      .catch((error) => console.error("Error fetching drives:", error));
  }, []);

  return (
    <div>
      <h1> Select a Drive to Browse</h1>
      <ul>
        {drives.map((drive) => (
          <li key={drive}>
            <Link to={`/drive/${drive}/`}>{drive}:/</Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default DrivePage;
