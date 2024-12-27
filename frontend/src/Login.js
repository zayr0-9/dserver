// Login.js

import React, { useState } from "react";
import axios from "axios";
import { getCSRFToken } from "./utils";
import { useNavigate } from "react-router-dom";

function Login({ setIsAuthenticated }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();

    const data = { username, password };

    axios
      .post("/api/auth/login/", data, {
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        withCredentials: true,
      })
      .then((response) => {
        setIsAuthenticated(true);
        navigate("/"); // Redirect to home or desired page
      })
      .catch((error) => {
        if (error.response && error.response.status === 401) {
          setErrorMessage("Invalid username or password");
        } else {
          setErrorMessage("An error occurred during login");
        }
      });
  };

  return (
    <div className="login-container">
      <h2>Login</h2>
      <form onSubmit={handleLogin}>
        <label>
          Username:
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </label>
        <label>
          Password:
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {errorMessage && <div className="error">{errorMessage}</div>}
        <button type="submit">Login</button>
      </form>
    </div>
  );
}

export default Login;
