'use client';

import { Mic, Settings, HelpCircle, Wifi, WifiOff } from 'lucide-react';

interface HeaderProps {
  isConnected: boolean;
  isConnecting?: boolean;
  onSettingsClick: () => void;
  onHelpClick: () => void;
}

export function Header({ isConnected, isConnecting, onSettingsClick, onHelpClick }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-200" role="banner">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Left: App name with icon */}
        <div className="flex items-center gap-2">
          <Mic className="w-6 h-6 text-blue-600" aria-hidden="true" />
          <h1 className="text-2xl font-bold text-gray-900">MedDictate</h1>
        </div>

        {/* Center: Tagline */}
        <div className="hidden sm:block">
          <p className="text-sm text-gray-500">Medical Voice Dictation</p>
        </div>

        {/* Right: Status and actions */}
        <div className="flex items-center gap-4">
          {/* Connection status */}
          {isConnecting ? (
            <div className="flex items-center gap-2 animate-pulse">
              <Wifi className="w-4 h-4 text-yellow-500" aria-hidden="true" />
              <span className="text-sm font-medium text-yellow-600">
                Connecting...
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {isConnected ? (
                <Wifi className="w-4 h-4 text-green-500" aria-hidden="true" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" aria-hidden="true" />
              )}
              <span className="text-sm font-medium text-gray-700">
                {isConnected ? 'Online' : 'Offline'}
              </span>
            </div>
          )}

          {/* Settings button */}
          <button
            onClick={onSettingsClick}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Open settings"
            tabIndex={0}
          >
            <Settings className="w-5 h-5 text-gray-600 hover:text-gray-900" aria-hidden="true" />
          </button>

          {/* Help button */}
          <button
            onClick={onHelpClick}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Show keyboard shortcuts"
            tabIndex={0}
          >
            <HelpCircle className="w-5 h-5 text-gray-600 hover:text-gray-900" aria-hidden="true" />
          </button>
        </div>
      </div>
    </header>
  );
}
