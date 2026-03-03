'use client';

import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { MacroManager } from './MacroManager';
import { SessionHistory, Session } from './SessionHistory';

interface SidebarProps {
  macros: any[];
  sessions: Session[];
  onInsertMacro: (expansion: string) => void;
  onLoadSession: (session: Session) => void;
  onDeleteSession: (id: string) => void;
  onUpdateSession: (session: Session) => void;
  onExportSession: (session: Session) => void;
  isMobileOpen: boolean;
  onToggleMobile: () => void;
}

export function Sidebar({
  macros,
  sessions,
  onInsertMacro,
  onLoadSession,
  onDeleteSession,
  onUpdateSession,
  onExportSession,
  isMobileOpen,
  onToggleMobile,
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<'macros' | 'history'>('macros');

  return (
    <>
      {/* Sidebar */}
      <aside
        className={`sidebar fixed lg:static w-72 h-full bg-white border-r border-gray-200 flex flex-col overflow-hidden transition-transform z-40 lg:z-auto ${isMobileOpen ? 'translate-x-0 sidebar-mobile-open' : '-translate-x-full lg:translate-x-0'
          }`}
        role="complementary"
        aria-label="Sidebar navigation"
      >
        {/* Tabs */}
        <div className="flex border-b border-gray-200 sticky top-0 bg-white" role="tablist" aria-label="Sidebar tabs">
          <button
            onClick={() => setActiveTab('macros')}
            className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'macros'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            role="tab"
            aria-selected={activeTab === 'macros'}
            aria-controls="sidebar-panel-macros"
            id="sidebar-tab-macros"
            tabIndex={0}
          >
            Macros
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'history'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            role="tab"
            aria-selected={activeTab === 'history'}
            aria-controls="sidebar-panel-history"
            id="sidebar-tab-history"
            tabIndex={0}
          >
            History
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'macros' && (
            <div role="tabpanel" id="sidebar-panel-macros" aria-labelledby="sidebar-tab-macros">
              <MacroManager onInsertMacro={onInsertMacro} />
            </div>
          )}
          {activeTab === 'history' && (
            <div role="tabpanel" id="sidebar-panel-history" aria-labelledby="sidebar-tab-history">
              <SessionHistory
                sessions={sessions}
                onLoadSession={onLoadSession}
                onDeleteSession={onDeleteSession}
                onUpdateSession={onUpdateSession}
                onExportSession={onExportSession}
              />
            </div>
          )}
        </div>

        {/* Footer helper text */}
        <div className="border-t border-gray-200 p-4 text-xs text-gray-500 text-center">
          Say trigger phrase while recording to auto-insert
        </div>
      </aside>

      {/* Mobile Toggle Button */}
      <button
        onClick={onToggleMobile}
        className="fixed lg:hidden bottom-20 right-4 z-50 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        aria-label={isMobileOpen ? 'Close sidebar' : 'Open sidebar'}
        aria-expanded={isMobileOpen}
        tabIndex={0}
      >
        {isMobileOpen ? <X className="w-5 h-5" aria-hidden="true" /> : <Menu className="w-5 h-5" aria-hidden="true" />}
      </button>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="fixed lg:hidden inset-0 bg-black bg-opacity-30 z-30 transition-opacity sidebar-overlay"
          onClick={onToggleMobile}
          aria-hidden="true"
        />
      )}
    </>
  );
}
