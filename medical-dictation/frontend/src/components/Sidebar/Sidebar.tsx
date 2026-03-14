// components/Sidebar/Sidebar.tsx
'use client';

import { useState } from 'react';
import { Menu, X, FileText, Clock, Zap } from 'lucide-react';
import { MacroManager } from './MacroManager';
import { TemplateManager } from './TemplateManager';
import { SessionHistory, Session } from './SessionHistory';
import { Macro } from '@/types';

interface SidebarProps {
  macros: Macro[];
  sessions: Session[];
  onInsertMacro: (text: string) => void;
  onInsertTemplate: (content: string) => void;
  onLoadSession: (session: Session) => void;
  onDeleteSession: (id: string) => void;
  onUpdateSession: (session: Session) => void;
  onExportSession: (session: Session) => void;
  onToast?: (message: string, type: 'success' | 'error' | 'info' | 'command') => void;
  isMobileOpen: boolean;
  onToggleMobile: () => void;
}

export function Sidebar({
  macros,
  sessions,
  onInsertMacro,
  onInsertTemplate,
  onLoadSession,
  onDeleteSession,
  onUpdateSession,
  onExportSession,
  onToast,
  isMobileOpen,
  onToggleMobile,
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<'templates' | 'macros' | 'history'>(
    'templates'
  );

  const tabs = [
    {
      id: 'templates' as const,
      label: 'Templates',
      icon: FileText,
    },
    {
      id: 'macros' as const,
      label: 'Macros',
      icon: Zap,
    },
    {
      id: 'history' as const,
      label: 'History',
      icon: Clock,
    },
  ];

  return (
    <>
      <aside
        className={`sidebar fixed lg:static w-72 h-full bg-white border-r border-gray-200 flex flex-col overflow-hidden transition-transform z-40 lg:z-auto ${
          isMobileOpen
            ? 'translate-x-0'
            : '-translate-x-full lg:translate-x-0'
        }`}
        role="complementary"
        aria-label="Sidebar navigation"
      >
        {/* Tabs */}
        <div
          className="flex border-b border-gray-200 sticky top-0 bg-white"
          role="tablist"
          aria-label="Sidebar tabs"
        >
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-3 text-xs font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`sidebar-panel-${tab.id}`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Templates Tab */}
          {activeTab === 'templates' && (
            <div
              role="tabpanel"
              id="sidebar-panel-templates"
              aria-label="Templates panel"
            >
              <TemplateManager
                onInsertTemplate={onInsertTemplate}
                onToast={onToast}
              />
            </div>
          )}

          {/* Macros Tab */}
          {activeTab === 'macros' && (
            <div
              role="tabpanel"
              id="sidebar-panel-macros"
              aria-label="Macros panel"
            >
              <MacroManager onInsertMacro={onInsertMacro} />
            </div>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <div
              role="tabpanel"
              id="sidebar-panel-history"
              aria-label="History panel"
            >
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

        {/* Footer */}
        <div className="border-t border-gray-200 p-3 text-xs text-gray-500 text-center">
          {activeTab === 'templates'
            ? 'Say "insert [template name]" while recording'
            : activeTab === 'macros'
            ? 'Say trigger phrase while recording to auto-insert'
            : `${sessions.length} sessions saved`}
        </div>
      </aside>

      {/* Mobile toggle button */}
      <button
        onClick={onToggleMobile}
        className="fixed lg:hidden bottom-20 right-4 z-50 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-lg"
        aria-label={isMobileOpen ? 'Close sidebar' : 'Open sidebar'}
        aria-expanded={isMobileOpen}
      >
        {isMobileOpen ? (
          <X className="w-5 h-5" />
        ) : (
          <Menu className="w-5 h-5" />
        )}
      </button>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed lg:hidden inset-0 bg-black bg-opacity-30 z-30 transition-opacity"
          onClick={onToggleMobile}
          aria-hidden="true"
        />
      )}
    </>
  );
}