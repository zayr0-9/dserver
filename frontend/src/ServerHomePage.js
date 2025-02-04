import React, { useEffect, useRef, useState } from 'react';
import styles from './ServerHomePage.module.css';
import { Link } from 'react-router-dom';
import * as THREE from 'three';
import VANTA from 'vanta/dist/vanta.net.min';

const ServerHomePage = () => {
  const vantaRef = useRef(null);
  const [vantaEffect, setVantaEffect] = useState(null);

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
    <div className={styles.homepage} ref={vantaRef}>
      <div className={styles.homepageBody}>
        <h1 className={styles.homepageTitle}>Welcome to the Server</h1>
        <div className={styles.homepageOptions}>
          <button className={styles.option}>
            <Link to="/drive/">File Mode</Link>
          </button>
          <button className={styles.option}>
            <Link to="/theatre-mode">Theatre Mode</Link>
          </button>
          <button className={styles.option}>
            <Link to="/admin-console">Admin Console</Link>
          </button>
          <button className={styles.option}>
            <Link to="/terminal">Terminal</Link>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ServerHomePage;
