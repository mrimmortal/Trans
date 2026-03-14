'use client';

import { useState, useEffect, useRef } from 'react';
import { Macro } from '@/types';
import { ChevronDown } from 'lucide-react';

interface TemplateDropdownProps {
  macros: Macro[];
  onInsert: (text: string) => void;
}

export function TemplateDropdown({ macros, onInsert }: TemplateDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Filter to only "Templates" category
  const templates = macros.filter((m) => m.category === 'Templates');

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleInsert = (text: string) => {
    onInsert(text);
    setIsOpen(false);
  };

  if (templates.length === 0) {
    return null;
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 rounded transition-colors"
        aria-label="Insert template"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        tabIndex={0}
      >
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>

      {isOpen && (
        <div
          className="absolute top-full right-0 mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
          role="listbox"
          aria-label="Templates"
        >
          {templates.map((template) => (
            <button
              key={template.id}
              // ✅ FIX: was template.expansion — Macro type has "text" not "expansion"
              onClick={() => handleInsert(template.text)}
              className="w-full text-left px-4 py-3 hover:bg-blue-50 text-sm text-gray-700 border-b last:border-b-0 transition-colors"
              role="option"
              aria-label={`Insert template: ${template.trigger}`}
              tabIndex={0}
            >
              <div className="font-semibold text-gray-900">{template.trigger}</div>
              <div className="text-xs text-gray-500 mt-1 line-clamp-1">
                {/* ✅ FIX: was template.expansion — Macro type has "text" not "expansion" */}
                {template.text.substring(0, 60)}...
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}