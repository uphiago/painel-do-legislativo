"use client";

import { useState, useCallback } from "react";

let toastId = 0;

export interface Toast {
  id: number;
  message: string;
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const show = useCallback((message: string) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 2500);
  }, []);

  return { toasts, show, ToastContainer: toasts.length > 0 ? (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className="toast">{t.message}</div>
      ))}
    </div>
  ) : null };
}
