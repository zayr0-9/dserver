import React from 'react';
import styles from './ServerHomePage.module.css';
import { Link } from 'react-router-dom';

const ServerHomePage = () => {
  return (
    <div className={styles.homepage}>
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
        </div>
      </div>
    </div>
  );
};

export default ServerHomePage;
