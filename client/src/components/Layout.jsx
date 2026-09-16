import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { User, BriefcaseBusiness, LogOut, ChevronDown } from "lucide-react";

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");

    // Agar Redux/auth context use kar rahi ho,
    // yahan apna logout action bhi dispatch kar dena.

    navigate("/login");
  };

  return (
    <nav className="w-full bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-50">

      {/* LEFT - LOGO */}
      <Link
        to="/"
        className="text-[22px] font-bold text-blue-600"
      >
        CareerSync
      </Link>

      {/* CENTER */}
      <div className="flex items-center gap-8">
        <Link
          to="/"
          className="text-[14px] font-medium text-gray-700 hover:text-blue-600"
        >
          Home
        </Link>

        <Link
          to="/about"
          className="text-[14px] font-medium text-gray-700 hover:text-blue-600"
        >
          About
        </Link>
      </div>

      {/* RIGHT - PROFILE */}
      <div className="relative">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-2 text-gray-700 hover:text-blue-600"
        >
          <User size={18} />

          <span className="text-[14px] font-medium">
            Profile
          </span>

          <ChevronDown
            size={15}
            className={`transition-transform ${
              open ? "rotate-180" : ""
            }`}
          />
        </button>

        {open && (
          <div className="absolute right-0 mt-3 w-48 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">

            <Link
              to="/profile"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-3 text-[13px] text-gray-700 hover:bg-gray-50"
            >
              <User size={16} />
              My Profile
            </Link>

            <Link
              to="/applications"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-3 text-[13px] text-gray-700 hover:bg-gray-50"
            >
              <BriefcaseBusiness size={16} />
              Applications
            </Link>

            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-3 text-[13px] text-red-600 hover:bg-red-50"
            >
              <LogOut size={16} />
              Logout
            </button>

          </div>
        )}
      </div>
    </nav>
  );
}