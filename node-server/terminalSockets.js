// const http = require('http');
// const WebSocket = require('ws');
// const terminalSockets = require('./terminalSockets');

// const server = http.createServer((req, res) => {
//     res.writeHead(200);
//     res.end("WebSocekt Server is running");
// });

// const wss = new WebSocket.server({server});

// wss.on("connection", (ws,rq) => {
//     const url = req.url;
//     if (url === "/terminal") {
//         terminalSockets.handleTerminalConnection(ws);
//     }
//     else {
//         ws.close(1000, "Invalid Websocket Endpoint")
//     }
// });

// const PORT = 8080;
// server.listen(PORT, () => {
//     console.log(`Server is running on http://localhost:${PORT}`)
// })