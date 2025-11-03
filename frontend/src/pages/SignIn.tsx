import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../supabaseClient";


declare global {
  interface Window {
    google: any;
  }
}

const SignIn = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const googleDivRef = useRef<HTMLDivElement>(null);
  const googleClientID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string;
  

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    const { error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      setErrorMsg(error.message);
    } else {
      navigate("/translate");
    }
  };

  useEffect(() => {
    const initializeGoogle = async () => {
      if (window.google && googleDivRef.current) {
        window.google.accounts.id.initialize({
          client_id: googleClientID, 
          callback: async (response: any) => {
            if (!response.credential) {
              setErrorMsg("Google sign-in failed. No credentials received.");
              return;
            }

            const { error } = await supabase.auth.signInWithIdToken({
              provider: "google",
              token: response.credential,
            });

            if (error) setErrorMsg(error.message);
            else navigate("/translate");
          },
        });

        window.google.accounts.id.renderButton(googleDivRef.current, {
          type: "standard",
          shape: "rectangular",
          theme: "outline",
          text: "signin_with",
          size: "medium",
        });

      }
    };

    initializeGoogle();
  }, []);

  return (
    <div className="auth-form">
      <h2>Sign In</h2>
      {errorMsg && <p className="error">{errorMsg}</p>}

      <form onSubmit={handleEmailSignIn}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        /><br />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        /><br />
        <button type="submit">Sign In</button>
      </form>

      <hr />

      <button type="submit" onClick={() => navigate('/signup')}>
        Sign Up
      </button>

      <div ref={googleDivRef} />
    </div>
  );
};

export default SignIn;
