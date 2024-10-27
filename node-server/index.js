const express = require("express");
const http = require("http");
const socketIO = require("socket.io");

// Initialize express and create an HTTP server
const app = express();
const server = http.createServer(app);

// Middleware to parse JSON
app.use(express.json()); // This is the missing middleware

// Set up Socket.IO
const io = socketIO(server);

// Listen for incoming connections
io.on("connection", (socket) => {
  console.log("New client connected");

  // Listen for file upload progress (or any custom event)
  socket.on("upload-progress", (data) => {
    // Broadcast progress to all clients
    io.emit("progress", data);
  });

  socket.on("disconnect", () => {
    console.log("Client disconnected");
  });
});

// Endpoint for receiving upload success messages
app.post("/upload-success", (req, res) => {
  const data = req.body;

  // Emit the message to all connected clients via Socket.IO
  if (data.message) {
    io.emit("notification", data.message);
    res.status(200).send("Notification sent");
  } else {
    res.status(400).send("No message found in the request.");
  }
});

// Set up the server to listen on port 3000
server.listen(3000, () => {
  console.log("Node.js server running on port 3000");
});
