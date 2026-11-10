import { Routes, Route } from "react-router-dom";
import AmbientBackground from "./components/AmbientBackground.jsx";
import Home from "./pages/Home.jsx";
import LiveDemo from "./pages/LiveDemo.jsx";

export default function App() {
  return (
    <>
      <AmbientBackground />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/demo" element={<LiveDemo />} />
      </Routes>
    </>
  );
}
