import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useSupabase } from "../contexts/SupabaseContext";

type ProtectedRouteProps = {
  children: ReactNode;
};

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { session } = useSupabase();
  return session ? children : <Navigate to="/signin" />;
}

export default ProtectedRoute;