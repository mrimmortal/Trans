'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { ChevronRight, CheckCircle, XCircle, Info, Command } from 'lucide-react';

// Types
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

// Context
const ToastContext = createContext<ToastContextValue | null>(null);

// Provider Component
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: ToastType) => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    const newToast: Toast = {
      id,
      message,
      type,
      createdAt: Date.now(),
    };

    setToasts((prev) => {
      const updated = [newToast, ...prev];
      // Keep only last 3 toasts
      return updated.slice(0, 3);
    });

    // Auto-remove after 3 seconds
    const timer = setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);

    return () => clearTimeout(timer);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

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
      <div className="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none">
        {toasts.map((toast) => {
          const styles = getToastStyles(toast.type);
          return (
            <div
              key={toast.id}
              className={`
                ${styles.bg} text-white
                rounded-lg shadow-lg p-4
                flex items-center gap-3
                min-w-max max-w-md
                pointer-events-auto
                animate-slide-in-right
                cursor-pointer
              `}
              onClick={() => removeToast(toast.id)}
              role="alert"
              aria-live="polite"
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
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>

      {/* Animation styles */}
      <style>{`
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

        @keyframes fadeOut {
          to {
            opacity: 0;
            transform: translateX(100%);
          }
        }

        .animate-slide-in-right {
          animation: slideInRight 0.3s ease-out;
        }

        @media (prefers-reduced-motion: reduce) {
          .animate-slide-in-right {
            animation: none;
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </ToastContext.Provider>
  );
}

// Hook
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}
