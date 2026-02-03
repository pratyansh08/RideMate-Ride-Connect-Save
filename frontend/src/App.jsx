import { Routes, Route, Navigate } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import CreateTrip from "./pages/CreateTrip.jsx";
import SearchTrips from "./pages/SearchTrips.jsx";
import TripDetail from "./pages/TripDetail.jsx";
import MyTrips from "./pages/MyTrips.jsx";
import MyBookings from "./pages/MyBookings.jsx";
import GiveReview from "./pages/GiveReview.jsx";
import TripReviews from "./pages/TripReviews.jsx";
import TripChat from "./pages/TripChat.jsx";

const App = () => {
  return (
    <div className="min-h-screen text-ink">
      <Navbar />
      <div className="mx-auto w-full max-w-6xl px-4 pb-16 pt-10">
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/trips/search" element={<SearchTrips />} />
          <Route path="/trips/:id" element={<TripDetail />} />
          <Route
            path="/chat/trip/:id"
            element={
              <ProtectedRoute>
                <TripChat />
              </ProtectedRoute>
            }
          />
          <Route
            path="/trips/create"
            element={
              <ProtectedRoute>
                <CreateTrip />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/trips"
            element={
              <ProtectedRoute>
                <MyTrips />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/bookings"
            element={
              <ProtectedRoute>
                <MyBookings />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reviews/new"
            element={
              <ProtectedRoute>
                <GiveReview />
              </ProtectedRoute>
            }
          />
          <Route path="/reviews/trip" element={<TripReviews />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    </div>
  );
};

export default App;
