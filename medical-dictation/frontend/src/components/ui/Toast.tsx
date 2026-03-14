// components/ui/Toast.tsx
'use client';

import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { CheckCircle, XCircle, Info, Command, X } from 'lucide-react';

// ═══════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════

export type ToastType = 'success' | 'error' | 'info' | 'command';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  createdAt: number;
}

interface ToastContextValue {
  showToast: (message: string, type: ToastType) => void;
}

// ═══════════════════════════════════════════════════════════════
// CONTEXT
// ═══════════════════════════════════════════════════════════════

const ToastContext = createContext<ToastContextValue | null>(null);

// ═══════════════════════════════════════════════════════════════
// PROVIDER
// ═══════════════════════════════════════════════════════════════

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    // Clear any existing timer
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      const newToast: Toast = {
        id,
        message,
        type,
        createdAt: Date.now(),
      };

      setToasts((prev) => {
        const updated = [newToast, ...prev];
        return updated.slice(0, 3); // Keep only last 3
      });

      // Auto-remove after 3 seconds
      const timer = setTimeout(() => {
        removeToast(id);
      }, 3000);

      timersRef.current.set(id, timer);
    },
    [removeToast]
  );

  // Get icon and colors by type
  const getToastStyles = (type: ToastType) => {
    switch (type) {
      case 'success':
        return {
          bg: 'bg-green-500',
          icon: <CheckCircle className="w-5 h-5" />,
        };
      case 'error':
        return {
          bg: 'bg-red-500',
          icon: <XCircle className="w-5 h-5" />,
        };
      case 'info':
        return {
          bg: 'bg-blue-500',
          icon: <Info className="w-5 h-5" />,
        };
      case 'command':
        return {
          bg: 'bg-purple-500',
          icon: <Command className="w-5 h-5" />,
        };
    }
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}

      {/* Toast Container */}
      <div
        className="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none"
        aria-live="polite"
      >
        {toasts.map((toast) => {
          const styles = getToastStyles(toast.type);
          return (
            <div
              key={toast.id}
              className={`${styles.bg} text-white rounded-lg shadow-lg p-4 flex items-center gap-3 min-w-[200px] max-w-md pointer-events-auto cursor-pointer animate-slide-in-right`}
              onClick={() => removeToast(toast.id)}
              role="alert"
            >
              <div className="flex-shrink-0">{styles.icon}</div>
              <div className="flex-1 text-sm font-medium">{toast.message}</div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeToast(toast.id);
                }}
                className="flex-shrink-0 ml-2 hover:opacity-80 transition-opacity"
                aria-label="Close notification"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>

      <style jsx global>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        .animate-slide-in-right {
          animation: slideInRight 0.3s ease-out;
        }

        @media (prefers-reduced-motion: reduce) {
          .animate-slide-in-right {
            animation: none;
          }
        }
      `}</style>
    </ToastContext.Provider>
  );
}

// ═══════════════════════════════════════════════════════════════
// HOOK
// ═══════════════════════════════════════════════════════════════

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}