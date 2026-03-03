'use client';

import { useState, useEffect } from 'react';
import { Mic, Trash2, Download, Edit2, ChevronLeft } from 'lucide-react';

export interface Session {
  id: string;
  title: string;
  content: string; // HTML
  plainText: string;
  wordCount: number;
  duration?: number; // seconds
  createdAt: string; // ISO date
  updatedAt?: string; // ISO date
}

interface SessionHistoryProps {
  sessions: Session[];
  onLoadSession: (session: Session) => void;
  onDeleteSession: (id: string) => void;
  onUpdateSession: (session: Session) => void;
  onExportSession: (session: Session) => void;
}

export function SessionHistory({
  sessions,
  onLoadSession,
  onDeleteSession,
  onUpdateSession,
  onExportSession,
}: SessionHistoryProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredSessions, setFilteredSessions] = useState<Session[]>(sessions);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      const query = searchQuery.toLowerCase();
      const filtered = sessions.filter(
        (s) =>
          s.title.toLowerCase().includes(query) ||
          s.plainText.toLowerCase().includes(query)
      );
      setFilteredSessions(filtered);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery, sessions]);

  // Format date
  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const isToday =
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear();

    const isYesterday =
      date.getDate() === yesterday.getDate() &&
      date.getMonth() === yesterday.getMonth() &&
      date.getFullYear() === yesterday.getFullYear();

    if (isToday) {
      return 'Today ' + date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    }

    if (isYesterday) {
      return 'Yesterday';
    }

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year:
        date.getFullYear() !== today.getFullYear()
          ? 'numeric'
          : undefined,
    });
  };

  // Format duration
  const formatDuration = (seconds?: number): string => {
    if (!seconds) return '';
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (minutes === 0) return `${secs}s`;
    return `${minutes}m ${secs}s`;
  };

  // Handle load with confirmation
  const handleLoadSession = (session: Session) => {
    if (
      window.confirm('Load this session? Unsaved content will be lost.')
    ) {
      onLoadSession(session);
    }
  };

  // Handle rename
  const handleRename = (session: Session, newTitle: string) => {
    if (newTitle.trim()) {
      const updated = { ...session, title: newTitle.trim(), updatedAt: new Date().toISOString() };
      onUpdateSession(updated);
    }
    setRenamingId(null);
    setRenameValue('');
  };

  if (sessions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-8 text-center">
        <Mic className="w-12 h-12 text-gray-300 mb-3" aria-hidden="true" />
        <p className="text-sm text-gray-500">No dictations yet</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Search */}
      <input
        type="text"
        placeholder="Search sessions..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Search sessions"
        tabIndex={0}
      />

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto space-y-2" role="list" aria-label="Session history">
        {filteredSessions.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">
            No results found
          </p>
        ) : (
          filteredSessions
            .sort(
              (a, b) =>
                new Date(b.createdAt).getTime() -
                new Date(a.createdAt).getTime()
            )
            .map((session) => (
              <div
                key={session.id}
                onMouseEnter={() => setHoveredId(session.id)}
                onMouseLeave={() => setHoveredId(null)}
                className="p-3 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors group"
                role="listitem"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0 cursor-pointer flex-col">
                    {renamingId === session.id ? (
                      <input
                        autoFocus
                        type="text"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() =>
                          handleRename(session, renameValue)
                        }
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            handleRename(session, renameValue);
                          } else if (e.key === 'Escape') {
                            setRenamingId(null);
                            setRenameValue('');
                          }
                        }}
                        className="w-full px-2 py-1 border border-blue-500 rounded text-sm focus:outline-none"
                        onClick={(e) => e.stopPropagation()}
                        aria-label="Rename session"
                        tabIndex={0}
                      />
                    ) : (
                      <>
                        <div
                          className="font-semibold text-sm text-gray-900 truncate"
                          onClick={() => handleLoadSession(session)}
                        >
                          {session.title}
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-600">
                          <span>{formatDate(session.createdAt)}</span>
                          <span>·</span>
                          <span>
                            {session.wordCount} words
                            {session.duration ? ` · ${formatDuration(session.duration)}` : ''}
                          </span>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Action buttons (show on hover) */}
                  {hoveredId === session.id && renamingId !== session.id && (
                    <div className="flex gap-1 flex-shrink-0">
                      <button
                        onClick={() => handleLoadSession(session)}
                        className="p-1 text-blue-600 hover:bg-blue-100 rounded transition-colors"
                        aria-label={`Load session: ${session.title}`}
                        tabIndex={0}
                      >
                        <ChevronLeft className="w-4 h-4" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() => {
                          setRenamingId(session.id);
                          setRenameValue(session.title);
                        }}
                        className="p-1 text-gray-600 hover:bg-gray-200 rounded transition-colors"
                        aria-label={`Rename session: ${session.title}`}
                        tabIndex={0}
                      >
                        <Edit2 className="w-4 h-4" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() => onExportSession(session)}
                        className="p-1 text-gray-600 hover:bg-gray-200 rounded transition-colors"
                        aria-label={`Export session: ${session.title}`}
                        tabIndex={0}
                      >
                        <Download className="w-4 h-4" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() => {
                          if (
                            window.confirm('Delete this session?')
                          ) {
                            onDeleteSession(session.id);
                          }
                        }}
                        className="p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 rounded transition-colors"
                        aria-label={`Delete session: ${session.title}`}
                        tabIndex={0}
                      >
                        <Trash2 className="w-4 h-4" aria-hidden="true" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))
        )}
      </div>
    </div>
  );
}
