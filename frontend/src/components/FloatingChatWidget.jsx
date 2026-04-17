import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import Chat from "./Chat.jsx";


const FloatingChatWidget = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);

  if (location.pathname === "/assistant") {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex max-h-[calc(100vh-5rem)] items-end justify-end">
      {isOpen ? (
        <div className="flex max-h-[calc(100vh-5rem)] w-[min(22rem,calc(100vw-1.5rem))] flex-col overflow-hidden rounded-[1.5rem] shadow-2xl">
          <Chat
            embedded
            onClose={() => setIsOpen(false)}
            onOpenFull={() => {
              setIsOpen(false);
              navigate("/assistant");
            }}
          />
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="rounded-full bg-ink px-4 py-3 text-sm font-semibold text-white shadow-2xl transition hover:opacity-90"
        >
          Open RideMate AI
        </button>
      )}
    </div>
  );
};

export default FloatingChatWidget;
