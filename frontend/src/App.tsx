import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { supabase } from "./supabaseClient";
import Home from "./pages/Home";
import Translate from "./pages/Translate";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";
import ProtectedRoute from "./components/ProtectedRoute";
import NavBar from "./components/NavBar";


function App() {
  // const { session, isLoading } = useSessionContext();

  // if (isLoading) return <div>Loading...</div>;
  function LogOut() {
  useEffect(() => {
    const doLogout = async () => {
      await supabase.auth.signOut();  // ✅ Proper logout
      localStorage.clear();           // optional, if you're storing anything extra
    };
    doLogout();
  }, []);
  return <Navigate to="/signin" />;
}

function SignUpAndLogout() {
  const [isLoggedOut, setIsLoggedOut] = useState(false);

  useEffect(() => {
    const logoutAndRedirectToSignUp = async () => {
      await supabase.auth.signOut();
      localStorage.clear();
      setIsLoggedOut(true);
    };

    logoutAndRedirectToSignUp();
  }, []);

  if (!isLoggedOut) return null; // Prevent showing SignUp until logout is done

  return <SignUp />;
}

function SignInAndLogout() {
  const [isLoggedOut, setIsLoggedOut] = useState(false);

  useEffect(() => {
    const logoutAndRedirectToSignIn = async () => {
      await supabase.auth.signOut();
      localStorage.clear();
      setIsLoggedOut(true);
    };

    logoutAndRedirectToSignIn();
  }, []);

  if (!isLoggedOut) return null; // Prevent showing SignIn until logout is done

  return <SignIn />;
}
  return (
    <div className="app-container">
      <NavBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/translate" element={
            <ProtectedRoute>
                <Translate />
            </ProtectedRoute>
        } />
        <Route path="/signin" element={<SignInAndLogout />} />
        <Route path="/signup" element={<SignUpAndLogout />} />
        <Route path="/logout" element={<LogOut />} />
      </Routes>
    </div>
  );
}

export default App;
