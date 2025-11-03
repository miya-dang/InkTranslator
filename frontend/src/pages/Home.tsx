import { Link } from "react-router-dom";


const Home = () => {
//   const session = useSupabase().session;

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}

        {/* <nav className="space-x-4">
          <Link to="/signin" className="hover:underline">Sign In</Link>
          <Link to="/signup" className="hover:underline">Sign Up</Link>
          <Link to="/translate" className="hover:underline">Translate</Link>
        </nav> */}

      {/* Main Content */}
        <header className="bg-gray-100 text-center p-4 text-lg font-semibold">
            <h1 className="text-2xl">About</h1>
            
        </header>

        <main className="flex-grow p-6">
            <p className="text-gray-600">Translate your manga images effortlessly</p>

        </main>

      {/* Footer */}
      {/* <footer className="bg-gray-100 text-center p-4 text-sm text-gray-500">
        &copy; 2025 Manga Translate. All rights reserved.
      </footer> */}
    </div>
  );
};

export default Home;
