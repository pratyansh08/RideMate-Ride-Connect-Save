import { NavLink, useNavigate } from "react-router-dom";

import ConnectionStatus from "./ConnectionStatus.jsx";
import { clearToken, isAuthed } from "../utils/auth.js";

const linkBase = "chip-link";

const Navbar = () => {
  const navigate = useNavigate();
  const authed = isAuthed();

  const handleLogout = () => {
    clearToken();
    navigate("/login");
  };

  return (
    <header className="border-b border-black/10 bg-ink text-white">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-5">
        <div>
          <p className="font-display text-xl font-bold text-white">RideMate</p>
          <p className="text-xs text-white/70">Ride • Connect • Save</p>
        </div>
        <nav className="flex flex-wrap items-center gap-2 text-sm text-white/80">
          <ConnectionStatus />
          <NavLink className={`${linkBase} text-white/80 hover:text-white`} to="/assistant">
            AI Assistant
          </NavLink>
          <NavLink className={`${linkBase} text-white/80 hover:text-white`} to="/profile">
            Profile
          </NavLink>
          <NavLink className={`${linkBase} text-white/80 hover:text-white`} to="/trips/search">
            Search Trips
          </NavLink>
          <NavLink className={`${linkBase} text-white/80 hover:text-white`} to="/trips/create">
            Create Trip
          </NavLink>
          <NavLink className={`${linkBase} text-white/80 hover:text-white`} to="/dashboard/trips">
            My Trips
          </NavLink>
          <NavLink className={`${linkBase} text-white/80 hover:text-white`} to="/dashboard/bookings">
            My Bookings
          </NavLink>
          <NavLink className={`${linkBase} text-white/80 hover:text-white`} to="/reviews/trip">
            Reviews
          </NavLink>
          {authed ? (
            <button type="button" onClick={handleLogout} className="btn-soft">
              Logout
            </button>
          ) : (
            <NavLink className="btn-soft" to="/login">
              Login
            </NavLink>
          )}
        </nav>
      </div>
    </header>
  );
};

export default Navbar;
