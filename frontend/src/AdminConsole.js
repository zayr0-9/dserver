import React, { useEffect, useState } from 'react';
import axios from 'axios';
import styles from './AdminConsole.module.css';
import DriveLetterUpdate from './UpdateDefaultDrive';

const AdminConsole = () => {
  const [items, setItems] = useState([]);
  const [currentPath, setCurrentPath] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async (path = '') => {
    try {
      const response = await axios.get('/api/admin/console/', {
        params: { path },
      });
      setItems(response.data.items);
      setCurrentPath(response.data.current_path);
    } catch (err) {
      console.error(err);
      setError('Failed to load data.');
    }
  };

  const handleNavigate = (path) => {
    fetchAdminData(path);
  };

  return (
    <div>
      <div className={styles.topBar}>
        <h1>Admin Console</h1>
        <div>
          <a href="/manage-file-types" className={styles.uploadLink}>
            Manage File Type Categories
          </a>
        </div>
        <button onClick={() => (window.location.href = '/')}>Home</button>
      </div>
      <div>
        <DriveLetterUpdate />
      </div>

      <div className={styles.container}>
        <h2>Manage Directories</h2>
        {error && <p className={styles.error}>{error}</p>}
        <table className={styles.adminConsoleTable}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Size (bytes)</th>
              <th>Last Modified</th>
              <th>Actions</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.relative_path}>
                <td>
                  {item.is_dir ? (
                    <a
                      href="#!"
                      onClick={() => handleNavigate(item.relative_path)}
                    >
                      {item.name}
                    </a>
                  ) : (
                    item.name
                  )}
                </td>
                <td>{item.is_dir ? 'Directory' : 'File'}</td>
                <td>{item.size || ''}</td>
                <td>{item.modified}</td>
                <td>{/* Add action buttons */}</td>
                <td>{/* Add status buttons */}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminConsole;
