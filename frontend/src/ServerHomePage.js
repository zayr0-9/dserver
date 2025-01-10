import React, { useEffect, useState } from "react";
import "./ServerHomePage.css";
import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";
import AdminConsole from "./AdminConsole";

const ServerHomePage = () => {
  const navigate = useNavigate();

  const handleNavigate = (path) => {
    navigate(path);
  };

  return (
    <div className="homepage">
      <h1> Welcome to the Server</h1>
      <div className="options">
        <button className="option">
          <Link to="/drive/">File Mode</Link>
        </button>
        <button className="option">
          <Link to="/theatre-mode">Theatre Mode</Link>
        </button>
        <button className="option">
          <Link to="/admin-console">Admin Console</Link>
          
        </button>
        
      </div>
    </div>
  );
};

export default ServerHomePage;
