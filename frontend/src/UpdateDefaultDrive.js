import React, { useState } from "react";
import axios from "axios";

const DriveLetterUpdate = () => {
  const [driveLetter, setDriveLetter] = useState("");
  const [message, setMessage] = useState("");

  const handleUpdate = async () => {
    try {
      const response = await axios.post(
        "/api/update-drive-letter/", // Ensure this matches your backend route
        { drive_letter: driveLetter.toUpperCase() },
        { headers: { "Content-Type": "application/json" } }
      );
      setMessage(response.data.message || "Drive letter updated successfully!");
    } catch (error) {
      const errorMessage =
        error.response?.data?.error || "Failed to update drive letter.";
      setMessage(errorMessage);
    }
  };

  return (
    <div>
      <h2>Update Drive Letter</h2>
      <input
        type="text"
        placeholder="Enter new drive letter (e.g., D)"
        value={driveLetter}
        onChange={(e) => setDriveLetter(e.target.value)}
        maxLength={1} // Limit input to a single character
      />
      <button onClick={handleUpdate}>Update Drive Letter</button>
      {message && <p>{message}</p>}
    </div>
  );
};

export default DriveLetterUpdate;
