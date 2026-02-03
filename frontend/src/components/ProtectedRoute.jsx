import { Navigate } from "react-router-dom";

import { isAuthed } from "../utils/auth.js";

const ProtectedRoute = ({ children }) => {
  if (!isAuthed()) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

export default ProtectedRoute;
