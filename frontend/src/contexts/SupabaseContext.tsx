import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';

// Profile interface
interface Profile {
  name: string | null;
  email: string | null;
}

// Context type
interface SupabaseContextType {
  user: any;
  session: any;
  loading: boolean;
  profile: Profile | null;
}

// Default context value
const SupabaseContext = createContext<SupabaseContextType>({
  user: null,
  session: null,
  loading: true,
  profile: null,
});

export const SupabaseProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<any>(null);
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    const initSession = async () => {
      const { data } = await supabase.auth.getSession();
      const currentUser = data.session?.user ?? null;

      setSession(data.session);
      setUser(currentUser);

      if (currentUser) {
        setProfile({
          name: currentUser.user_metadata?.display_name ?? null,
          email: currentUser.email ?? null,
        });
      }

      setLoading(false);
    };

    initSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      const currentUser = session?.user ?? null;
      setUser(currentUser);

      if (currentUser) {
        setProfile({
          name: currentUser.user_metadata?.display_name ?? null,
          email: currentUser.email ?? null,
        });
      } else {
        setProfile(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  return (
    <SupabaseContext.Provider value={{ user, session, loading, profile }}>
      {children}
    </SupabaseContext.Provider>
  );
};

export const useSupabase = () => useContext(SupabaseContext);
