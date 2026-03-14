// components/Sidebar/MacroManager.tsx
'use client';

import { useState, useEffect } from 'react';
import { Macro } from '@/types';
import { DEFAULT_MACROS } from '@/lib/defaultMacros';
import { PlusCircle, X, ChevronDown } from 'lucide-react';

const STORAGE_KEY = 'medDictateMacros';
const CATEGORIES = [
  'Cardiovascular',
  'Respiratory',
  'Neurological',
  'Gastrointestinal',
  'Templates',
  'Vitals',
  'Custom',
];

interface MacroManagerProps {
  onInsertMacro: (text: string) => void;
}

/**
 * Migrate old localStorage macros that used `expansion` → `text`.
 */
function migrateMacros(raw: any[]): Macro[] {
  return raw.map((m) => ({
    id: m.id || `migrated-${Date.now()}-${Math.random()}`,
    name: m.name || m.trigger || '',
    trigger: m.trigger || '',
    text: m.text || m.expansion || '',
    category: m.category || 'Custom',
  }));
}

export function MacroManager({ onInsertMacro }: MacroManagerProps) {
  const [macros, setMacros] = useState<Macro[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [newTrigger, setNewTrigger] = useState('');
  const [newExpansion, setNewExpansion] = useState('');
  const [newCategory, setNewCategory] = useState('Custom');

  // Load macros from localStorage on mount with migration
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        const migrated = migrateMacros(parsed);
        setMacros(migrated);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated));
      } catch {
        setMacros(DEFAULT_MACROS);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_MACROS));
      }
    } else {
      setMacros(DEFAULT_MACROS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_MACROS));
    }
  }, []);

  // Filter macros by search query
  const filteredMacros = macros.filter(
    (m) =>
      m.trigger.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (m.text || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (m.category || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group macros by category
  const grouped = filteredMacros.reduce(
    (acc, macro) => {
      const cat = macro.category || 'Uncategorized';
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(macro);
      return acc;
    },
    {} as Record<string, Macro[]>
  );

  // Validate and add custom macro
  const handleAddMacro = () => {
    const triggerWords = newTrigger.trim().split(/\s+/).length;
    if (triggerWords < 2) {
      alert('Trigger must be at least 2 words');
      return;
    }
    if (!newExpansion.trim()) {
      alert('Expansion cannot be empty');
      return;
    }

    const macro: Macro = {
      id: `custom-${Date.now()}`,
      name: newTrigger.trim(),
      trigger: newTrigger.trim(),
      text: newExpansion.trim(),
      category: newCategory,
    };

    const updated = [...macros, macro];
    setMacros(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));

    setNewTrigger('');
    setNewExpansion('');
    setNewCategory('Custom');
    setIsFormOpen(false);
  };

  // Delete macro
  const handleDeleteMacro = (id: string) => {
    if (!window.confirm('Delete this macro?')) return;
    const updated = macros.filter((m) => m.id !== id);
    setMacros(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Search */}
      <input
        type="text"
        placeholder="Search macros..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Search macros"
      />

      {/* Macros by category */}
      <div className="space-y-4 max-h-96 overflow-y-auto" role="list" aria-label="Macros list">
        {Object.keys(grouped).length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">No macros found</p>
        )}

        {Object.entries(grouped).map(([category, categoryMacros]) => (
          <div key={category} role="group" aria-label={`${category} macros`}>
            <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
              {category}
            </h3>
            <div className="space-y-2">
              {categoryMacros.map((macro) => {
                const displayText = macro.text || '';

                return (
                  <div
                    key={macro.id}
                    className="p-3 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
                    role="listitem"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm text-gray-900">
                          {macro.trigger}
                        </div>
                        <div className="text-xs text-gray-600 mt-1 line-clamp-1">
                          {displayText.substring(0, 50)}
                          {displayText.length > 50 ? '...' : ''}
                        </div>
                      </div>
                      <div className="flex gap-1 flex-shrink-0">
                        <button
                          onClick={() => onInsertMacro(displayText)}
                          className="p-1 text-blue-600 hover:bg-blue-100 rounded transition-colors"
                          aria-label={`Insert macro: ${macro.trigger}`}
                        >
                          <PlusCircle className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteMacro(macro.id)}
                          className="p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 rounded transition-colors"
                          aria-label={`Delete macro: ${macro.trigger}`}
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Add Custom Macro */}
      <div className="border-t border-gray-200 pt-4">
        <button
          onClick={() => setIsFormOpen(!isFormOpen)}
          className="w-full flex items-center justify-between px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          aria-expanded={isFormOpen}
        >
          Add Custom Macro
          <ChevronDown
            className={`w-4 h-4 transition-transform ${isFormOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {isFormOpen && (
          <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
            <input
              type="text"
              placeholder="Trigger (e.g. 'normal heart exam')"
              value={newTrigger}
              onChange={(e) => setNewTrigger(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Macro trigger phrase"
            />

            <select
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Macro category"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            <textarea
              placeholder="Expansion text"
              value={newExpansion}
              onChange={(e) => setNewExpansion(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none h-24"
              aria-label="Macro expansion text"
            />

            <div className="flex gap-2">
              <button
                onClick={handleAddMacro}
                className="flex-1 px-3 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Save
              </button>
              <button
                onClick={() => setIsFormOpen(false)}
                className="flex-1 px-3 py-2 bg-gray-300 text-gray-700 rounded text-sm font-medium hover:bg-gray-400 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}