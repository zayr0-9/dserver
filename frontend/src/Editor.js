import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import axios from "axios";
// import "./Editor.css"; // Create a CSS file for custom styles

const FileEditor = () => {
  const { driveLetter, "*": pathParam } = useParams();
  const [fileContent, setFileContent] = useState("");
  const [language, setLanguage] = useState("plaintext");
  const [fileName, setFileName] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [editorOptions, setEditorOptions] = useState({
    theme: "vs-dark",
    fontSize: 14,
  });

  const currentPath = pathParam || "";

  useEffect(() => {
    // Fetch file content when component mounts
    fetchFileContent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [driveLetter, currentPath]);

  const fetchFileContent = () => {
    const data = {
      base_dir: driveLetter,
      relative_path: currentPath,
    };

    axios
      .post("/api/files/content/", data, {
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        withCredentials: true,
      })
      .then((response) => {
        if (response.data.success) {
          setFileContent(response.data.content);
          setFileName(response.data.name);
          setLanguage(detectLanguage(response.data.name));
        } else {
          alert(response.data.error || "Failed to load file content.");
        }
      })
      .catch((error) => {
        if (error.response && error.response.status === 409) {
          setErrorMessage("File is currently being edited by another user.");
        } else {
          // ... existing error handling ...

          console.error("Error fetching file content:", error);
          alert("An error occurred while fetching the file content.");
        }
      });
  };
  const getCSRFToken = () => {
    const name = "csrftoken";
    const cookies = document.cookie.split(";").map((cookie) => cookie.trim());
    for (let cookie of cookies) {
      if (cookie.startsWith(name + "=")) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return "";
  };
  const saveFileContent = () => {
    setIsSaving(true);

    const data = {
      base_dir: driveLetter,
      relative_path: currentPath,
      content: fileContent,
    };

    axios
      .post("/api/files/save/", data, {
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        withCredentials: true,
      })
      .then((response) => {
        if (response.data.success) {
          alert("File saved successfully.");
        } else {
          alert(response.data.error || "Failed to save the file.");
        }
        setIsSaving(false);
      })
      .catch((error) => {
        if (error.response && error.response.status === 403) {
          alert("You do not have permission to save this file.");
        } else {
          console.error("Error saving file:", error);
          alert("An error occurred while saving the file.");
          setIsSaving(false);
        }
      });
  };

  const detectLanguage = (fileName) => {
    const extension = fileName.split(".").pop();
    switch (extension) {
      case "js":
        return "javascript";
      case "py":
        return "python";
      case "html":
        return "html";
      case "css":
        return "css";
      case "json":
        return "json";
      case "md":
        return "markdown";
      // Add more cases for other languages
      default:
        return "plaintext";
    }
  };

  const handleEditorChange = (value) => {
    setFileContent(value);
  };

  const handleOptionChange = (e) => {
    setEditorOptions({
      ...editorOptions,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="editor-container">
      <div className="editor-toolbar">
        <h2>Editing: {fileName}</h2>
        <div className="editor-options">
          <label>
            Theme:
            <select
              name="theme"
              value={editorOptions.theme}
              onChange={handleOptionChange}
            >
              <option value="vs-light">Light</option>
              <option value="vs-dark">Dark</option>
            </select>
          </label>
          <label>
            Font Size:
            <input
              type="number"
              name="fontSize"
              value={editorOptions.fontSize}
              onChange={handleOptionChange}
              style={{ width: "60px" }}
            />
          </label>
          <button onClick={saveFileContent} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
      <Editor
        height="80vh"
        defaultLanguage={language}
        value={fileContent}
        onChange={handleEditorChange}
        theme={editorOptions.theme}
        options={{
          fontSize: parseInt(editorOptions.fontSize, 10),
          automaticLayout: true,
        }}
      />
    </div>
  );
};

export default FileEditor;
