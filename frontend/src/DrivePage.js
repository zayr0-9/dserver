import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import styles from './DrivePage.module.css';
import * as THREE from 'three';
import VANTA from 'vanta/dist/vanta.net.min';

const DrivePage = () => {
  const [drives, setDrives] = useState([]);
  const vantaRef = useRef(null);
  const [vantaEffect, setVantaEffect] = useState(null);
  useEffect(() => {
    fetch('/api/drives/')
      .then((response) => response.json())
      .then((data) => setDrives(data.drives))
      .catch((error) => console.error('Error fetching drives:', error));
  }, []);
  useEffect(() => {
    if (!vantaEffect) {
      // console.log('Initializing Vanta.js effect...');
      const effect = VANTA({
        el: vantaRef.current,
        THREE: THREE,
        mouseControls: true,
        touchControls: true,
        gyroControls: false,
        minHeight: 200.0,
        minWidth: 200.0,
        scale: 1.0,
        scaleMobile: 1.0,
        color: 0xf1c232, // Your custom color
        backgroundColor: '#0E0612', // Your custom background
        points: 10, // Number of points
        maxDistance: 0, // Max connection distance
        spacing: 15, // Space between points
        showDots: true, // Show the dots
        pointColor: 0xff3f81,
      });
      setVantaEffect(effect);
      // console.log('Vanta.js effect initialized:', effect);
    }

    // Cleanup Vanta.js effect on unmount
    return () => {
      if (vantaEffect) vantaEffect.destroy();
    };
  }, [vantaEffect]);
  return (
    <div className={styles.drives} ref={vantaRef}>
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
