import { useEffect, useState } from "react";

import api from "../api/client.js";

const ConnectionStatus = () => {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let isMounted = true;
    const check = async () => {
      try {
        await api.get("/");
        if (isMounted) setStatus("online");
      } catch (err) {
        if (isMounted) setStatus("offline");
      }
    };
    check();
    const timer = setInterval(check, 15000);
    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, []);

  const label =
    status === "online" ? "Connected" : status === "offline" ? "Disconnected" : "Checking...";
  const color =
    status === "online"
      ? "bg-lime/15 text-white border-lime/30"
      : status === "offline"
        ? "bg-red-500/20 text-white border-red-500/40"
        : "bg-white/10 text-white/80 border-white/20";

  return (
    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${color}`}>
      {label}
    </span>
  );
};

export default ConnectionStatus;
