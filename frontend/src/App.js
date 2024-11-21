import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import ServerHomePage from "./ServerHomePage";
import DrivePage from "./DrivePage";
import DriveContents from "./DriveContent";
// import AdminPage
function App() {
  return (
    <Router>
      <Routes>
        <Route exact path="/" element={<ServerHomePage />} />
        <Route path="/drive/" element={<DrivePage />} />
        <Route path="/drive/:driveLetter/*" element={<DriveContents />} />

        {/* Define route for other components here*/}
        {/* <Route path="/theatre-mode" element={TheatreMode} />
        <Route path="/admin" element={AdminPage} /> */}
      </Routes>
    </Router>
  );
}

// function App() {
//   const [videos, setVideos] = useState([]); // Store video data from the server
//   const [searchTerm, setSearchTerm] = useState(""); // Track search term
//   const [page, setPage] = useState(1); // Current page for pagination
//   const [hasNext, setHasNext] = useState(true); // Track if there are more pages to load

//   // Fetch videos from the backend (Django API)
//   const fetchVideos = (newPage = 1) => {
//     const queryParam = searchTerm ? `q=${searchTerm}&` : "";
//     fetch(`/api/videos/?${queryParam}page=${newPage}&page_size=20`)
//       .then((response) => response.json())
//       .then((data) => {
//         setVideos(newPage === 1 ? data.videos : [...videos, ...data.videos]);
//         setPage(newPage);
//         setHasNext(data.has_next);
//       })
//       .catch((error) => console.error("Error fetching videos:", error));
//   };

//   // Initial load or refresh when search term changes
//   useEffect(() => {
//     fetchVideos(1);
//   }, [searchTerm]);

//   // Function to handle the search input
//   const handleSearchChange = (event) => {
//     setSearchTerm(event.target.value);
//   };

//   // Function to load the next page of videos
//   const loadMoreVideos = () => {
//     if (hasNext) {
//       fetchVideos(page + 1);
//     }
//   };

//   return (
//     <Router basename="/theatre-mode">
//       <div className="App">
//         <header className="App-header">
//           <h1>Theatre Mode</h1>

//           {/* Search Bar */}
//           <input
//             type="text"
//             placeholder="Search for a video..."
//             value={searchTerm}
//             onChange={handleSearchChange}
//           />

//           <Routes>
//             <Route path="/" element={<VideoGrid videos={videos} />} />
//             <Route path="/video/:relative_path" element={<VideoPlayer />} />
//           </Routes>

//           {/* Load More Button */}
//           {hasNext && <button onClick={loadMoreVideos}>Load More</button>}
//         </header>
//       </div>
//     </Router>
//   );
// }

export default App;
