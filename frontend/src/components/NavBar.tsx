import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSupabase } from "../contexts/SupabaseContext";
import { supabase } from "../supabaseClient";


const NavBar: React.FC = () => {
  const { user } = useSupabase();
  const navigate = useNavigate();
  const displayName = user?.user_metadata?.name ?? user?.email;
  const currentPath = location.pathname;
  const isAuthPage = currentPath.startsWith("/signin") || currentPath.startsWith("/signup");
   
  const handleLogout = async () => {
    await supabase.auth.signOut();
    localStorage.clear();
    navigate("/signin");
  };

  return (
    <nav className="bg-white shadow p-4 flex justify-between items-center">
        <Link to="/">Ink Translator</Link>
            
        <div>
            {!user ? (
                // If not signed in, and not on signin/signup pages, show links
                !isAuthPage && (
                    <>
                        <Link to="/signin">Sign In</Link>
                        <Link to="/signup">Sign Up</Link>
                    </>
                )
            ) : (
            // If signed in, show username/email and log out button
            <>
                <div className="text-gray-800 font-medium">
                    {displayName}
                    <button onClick={handleLogout}>
                        Logout
                    </button>
                </div>
                
            </>
        )}
      </div>
    </nav>
  );
};

export default NavBar;
