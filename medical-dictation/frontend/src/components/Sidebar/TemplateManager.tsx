// components/Sidebar/TemplateManager.tsx
'use client';

import { useState, useEffect } from 'react';
import { useTemplates } from '@/hooks/useTemplates';
import type { Template, TemplateCreate } from '@/types';
import {
  PlusCircle,
  X,
  ChevronDown,
  ChevronUp,
  Search,
  RefreshCw,
  Edit2,
  Trash2,
  AlertCircle,
  FileText,
  Mic,
  Info,
  Copy,
  Check,
  HelpCircle,
  Volume2,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════

const TEMPLATE_CATEGORIES = [
  'clinical',
  'notes',
  'consultations',
  'custom',
  'general',
];

const CATEGORY_COLORS: Record<string, string> = {
  clinical: 'bg-blue-100 text-blue-700',
  notes: 'bg-green-100 text-green-700',
  consultations: 'bg-purple-100 text-purple-700',
  custom: 'bg-orange-100 text-orange-700',
  general: 'bg-gray-100 text-gray-700',
};

// ═══════════════════════════════════════════════════════════════
// PROPS
// ═══════════════════════════════════════════════════════════════

interface TemplateManagerProps {
  onInsertTemplate: (content: string) => void;
  onToast?: (message: string, type: 'success' | 'error' | 'info' | 'command') => void;
}

// ═══════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════

export function TemplateManager({ onInsertTemplate, onToast }: TemplateManagerProps) {
  const {
    templates,
    categories,
    isLoading,
    error,
    selectedCategory,
    searchQuery,
    setSelectedCategory,
    setSearchQuery,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    refreshTemplates,
    clearError,
  } = useTemplates();

  // ─────────────────────────────────────────────────────────
  // LOCAL STATE
  // ─────────────────────────────────────────────────────────

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [expandedTemplate, setExpandedTemplate] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showHowToUse, setShowHowToUse] = useState(false);
  const [showAllTriggers, setShowAllTriggers] = useState(false);
  const [copiedTrigger, setCopiedTrigger] = useState<string | null>(null);

  // Form fields
  const [formName, setFormName] = useState('');
  const [formTriggers, setFormTriggers] = useState('');
  const [formContent, setFormContent] = useState('');
  const [formCategory, setFormCategory] = useState('custom');
  const [formDescription, setFormDescription] = useState('');
  const [formAuthor, setFormAuthor] = useState('');
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // ─────────────────────────────────────────────────────────
  // COPY TRIGGER TO CLIPBOARD
  // ─────────────────────────────────────────────────────────

  const copyTrigger = async (phrase: string) => {
    try {
      await navigator.clipboard.writeText(`insert ${phrase}`);
      setCopiedTrigger(phrase);
      onToast?.(`Copied: "insert ${phrase}"`, 'info');
      setTimeout(() => setCopiedTrigger(null), 2000);
    } catch {
      // Fallback
      setCopiedTrigger(phrase);
      setTimeout(() => setCopiedTrigger(null), 2000);
    }
  };

  // ─────────────────────────────────────────────────────────
  // FORM HANDLERS
  // ─────────────────────────────────────────────────────────

  const resetForm = () => {
    setFormName('');
    setFormTriggers('');
    setFormContent('');
    setFormCategory('custom');
    setFormDescription('');
    setFormAuthor('');
    setFormErrors({});
    setEditingTemplate(null);
  };

  const openCreateForm = () => {
    resetForm();
    setIsFormOpen(true);
  };

  const openEditForm = (template: Template) => {
    setFormName(template.name);
    setFormTriggers(template.trigger_phrases.join(', '));
    setFormContent(template.content);
    setFormCategory(template.category);
    setFormDescription(template.description);
    setFormAuthor(template.author);
    setFormErrors({});
    setEditingTemplate(template);
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
    resetForm();
  };

  // ─────────────────────────────────────────────────────────
  // VALIDATION
  // ─────────────────────────────────────────────────────────

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formName.trim()) {
      errors.name = 'Name is required';
    } else if (!/^[a-z][a-z0-9_]*$/.test(formName.trim())) {
      errors.name = 'Use lowercase letters, numbers, underscores. Must start with a letter.';
    }

    if (!formTriggers.trim()) {
      errors.triggers = 'At least one trigger phrase is required';
    }

    if (!formContent.trim()) {
      errors.content = 'Content is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // ─────────────────────────────────────────────────────────
  // SUBMIT
  // ─────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setIsSubmitting(true);

    try {
      const triggerPhrases = formTriggers
        .split(',')
        .map((t) => t.trim().toLowerCase())
        .filter(Boolean);

      if (editingTemplate) {
        await updateTemplate(editingTemplate.name, {
          trigger_phrases: triggerPhrases,
          content: formContent,
          category: formCategory,
          description: formDescription,
          author: formAuthor,
        });
        onToast?.('Template updated successfully', 'success');
      } else {
        const data: TemplateCreate = {
          name: formName.trim().toLowerCase(),
          trigger_phrases: triggerPhrases,
          content: formContent,
          category: formCategory || 'custom',
          description: formDescription,
          author: formAuthor,
        };
        await createTemplate(data);
        onToast?.('Template created successfully', 'success');
      }

      closeForm();
    } catch (err: any) {
      setFormErrors({ submit: err.message || 'Failed to save template' });
      onToast?.(err.message || 'Failed to save template', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  // ─────────────────────────────────────────────────────────
  // DELETE
  // ─────────────────────────────────────────────────────────

  const handleDelete = async (name: string) => {
    if (!window.confirm(`Delete template "${name}"?`)) return;

    try {
      await deleteTemplate(name);
      onToast?.('Template deleted', 'success');
    } catch (err: any) {
      onToast?.(err.message || 'Failed to delete', 'error');
    }
  };

  // ─────────────────────────────────────────────────────────
  // INSERT
  // ─────────────────────────────────────────────────────────

  const handleInsert = (template: Template) => {
    onInsertTemplate(template.content);
    onToast?.(`Inserted "${template.name.replace(/_/g, ' ')}"`, 'command');
  };

  // ─────────────────────────────────────────────────────────
  // GROUP BY CATEGORY
  // ─────────────────────────────────────────────────────────

  const grouped = templates.reduce(
    (acc, template) => {
      const cat = template.category || 'general';
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(template);
      return acc;
    },
    {} as Record<string, Template[]>
  );

  // ═══════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════

  return (
    <div className="flex flex-col gap-3">

      {/* ═════════════════════════════════════════════════════════ */}
      {/* HOW TO USE BANNER                                       */}
      {/* ═════════════════════════════════════════════════════════ */}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <button
          onClick={() => setShowHowToUse(!showHowToUse)}
          className="w-full flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-2">
            <Mic className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold text-blue-800">
              How to use templates
            </span>
          </div>
          <ChevronDown
            className={`w-3.5 h-3.5 text-blue-600 transition-transform ${
              showHowToUse ? 'rotate-180' : ''
            }`}
          />
        </button>

        {showHowToUse && (
          <div className="mt-3 space-y-2 text-xs text-blue-700">
            <div className="flex items-start gap-2">
              <span className="bg-blue-200 text-blue-800 rounded-full w-4 h-4 flex items-center justify-center flex-shrink-0 text-[10px] font-bold mt-0.5">
                1
              </span>
              <span>
                <strong>Click [+]</strong> button on any template to insert it directly
              </span>
            </div>
            <div className="flex items-start gap-2">
              <span className="bg-blue-200 text-blue-800 rounded-full w-4 h-4 flex items-center justify-center flex-shrink-0 text-[10px] font-bold mt-0.5">
                2
              </span>
              <span>
                <strong>Say voice trigger</strong> while recording, e.g:
              </span>
            </div>
            <div className="ml-6 space-y-1">
              <div className="flex items-center gap-1.5">
                <Volume2 className="w-3 h-3 text-blue-500" />
                <code className="bg-blue-100 px-1.5 py-0.5 rounded text-[10px] font-mono">
                  &quot;insert vitals&quot;
                </code>
              </div>
              <div className="flex items-center gap-1.5">
                <Volume2 className="w-3 h-3 text-blue-500" />
                <code className="bg-blue-100 px-1.5 py-0.5 rounded text-[10px] font-mono">
                  &quot;insert soap note&quot;
                </code>
              </div>
              <div className="flex items-center gap-1.5">
                <Volume2 className="w-3 h-3 text-blue-500" />
                <code className="bg-blue-100 px-1.5 py-0.5 rounded text-[10px] font-mono">
                  &quot;add physical exam&quot;
                </code>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="bg-blue-200 text-blue-800 rounded-full w-4 h-4 flex items-center justify-center flex-shrink-0 text-[10px] font-bold mt-0.5">
                3
              </span>
              <span>
                <strong>Prefix options:</strong> &quot;insert [name]&quot;, &quot;add [name]&quot;, or just &quot;[name]&quot;
              </span>
            </div>
            <div className="flex items-start gap-2 pt-1 border-t border-blue-200">
              <Info className="w-3.5 h-3.5 text-blue-500 flex-shrink-0 mt-0.5" />
              <span>
                Click on any{' '}
                <span className="bg-green-100 text-green-700 px-1 py-0.5 rounded text-[10px] font-mono">
                  trigger phrase
                </span>{' '}
                below to copy it
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ═════════════════════════════════════════════════════════ */}
      {/* SHOW ALL TRIGGERS BUTTON                                 */}
      {/* ═════════════════════════════════════════════════════════ */}

      <button
        onClick={() => setShowAllTriggers(!showAllTriggers)}
        className={`flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
          showAllTriggers
            ? 'bg-green-100 text-green-800 border border-green-300'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
        }`}
      >
        <Volume2 className="w-3.5 h-3.5" />
        {showAllTriggers ? 'Hide All Triggers' : 'Show All Voice Triggers'}
        <span className="bg-gray-200 text-gray-700 px-1.5 py-0.5 rounded-full text-[10px] font-bold">
          {templates.reduce((sum, t) => sum + t.trigger_phrases.length, 0)}
        </span>
      </button>

      {/* ═════════════════════════════════════════════════════════ */}
      {/* ALL TRIGGERS PANEL                                       */}
      {/* ═════════════════════════════════════════════════════════ */}

      {showAllTriggers && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 max-h-64 overflow-y-auto">
          <div className="flex items-center gap-2 mb-3">
            <Volume2 className="w-4 h-4 text-green-700" />
            <h4 className="text-xs font-bold text-green-800 uppercase tracking-wider">
              Voice Trigger Quick Reference
            </h4>
          </div>

          <div className="space-y-3">
            {templates.map((template) => (
              <div key={template.id} className="flex items-start gap-2">
                {/* Template name */}
                <div className="flex-shrink-0 w-28">
                  <span className="text-[11px] font-semibold text-gray-800 truncate block">
                    {template.name.replace(/_/g, ' ')}
                  </span>
                  <span
                    className={`inline-block px-1 py-0.5 text-[9px] font-medium rounded mt-0.5 ${
                      CATEGORY_COLORS[template.category] || CATEGORY_COLORS.general
                    }`}
                  >
                    {template.category}
                  </span>
                </div>

                {/* Trigger phrases */}
                <div className="flex-1 flex flex-wrap gap-1">
                  {template.trigger_phrases.map((phrase, i) => (
                    <button
                      key={i}
                      onClick={() => copyTrigger(phrase)}
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono transition-colors cursor-pointer ${
                        copiedTrigger === phrase
                          ? 'bg-green-200 text-green-800'
                          : 'bg-white text-green-700 border border-green-200 hover:bg-green-100'
                      }`}
                      title={`Click to copy: "insert ${phrase}"`}
                    >
                      {copiedTrigger === phrase ? (
                        <Check className="w-2.5 h-2.5" />
                      ) : (
                        <Volume2 className="w-2.5 h-2.5 opacity-50" />
                      )}
                      &quot;{phrase}&quot;
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-3 pt-2 border-t border-green-200 text-[10px] text-green-600">
            💡 Say <strong>&quot;insert [trigger]&quot;</strong> or{' '}
            <strong>&quot;add [trigger]&quot;</strong> while recording.
            Click any trigger to copy it.
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════ */}
      {/* SEARCH & ACTIONS                                         */}
      {/* ═════════════════════════════════════════════════════════ */}

      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search templates or triggers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          onClick={() => refreshTemplates()}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
          title="Refresh templates"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* ═════════════════════════════════════════════════════════ */}
      {/* CATEGORY FILTER                                          */}
      {/* ═════════════════════════════════════════════════════════ */}

      {categories.length > 0 && (
        <div className="flex gap-1.5 flex-wrap">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-2.5 py-1 text-xs font-medium rounded-full transition-colors ${
              !selectedCategory
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            All ({templates.length})
          </button>
          {categories.map((cat) => {
            const count = templates.filter((t) => t.category === cat).length;
            return (
              <button
                key={cat}
                onClick={() =>
                  setSelectedCategory(selectedCategory === cat ? null : cat)
                }
                className={`px-2.5 py-1 text-xs font-medium rounded-full transition-colors ${
                  selectedCategory === cat
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {cat} ({count})
              </button>
            );
          })}
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════ */}
      {/* ERROR                                                    */}
      {/* ═════════════════════════════════════════════════════════ */}

      {error && (
        <div className="flex items-start gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-red-700 flex-1">{error}</p>
          <button onClick={clearError} className="text-red-400 hover:text-red-600">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════ */}
      {/* LOADING                                                  */}
      {/* ═════════════════════════════════════════════════════════ */}

      {isLoading && templates.length === 0 && (
        <div className="flex items-center justify-center py-8">
          <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════ */}
      {/* EMPTY STATE                                              */}
      {/* ═════════════════════════════════════════════════════════ */}

      {!isLoading && templates.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <FileText className="w-10 h-10 text-gray-300 mb-2" />
          <p className="text-sm text-gray-500">No templates found</p>
          <p className="text-xs text-gray-400 mt-1">
            Create one or check your backend connection
          </p>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════ */}
      {/* TEMPLATES LIST                                           */}
      {/* ═════════════════════════════════════════════════════════ */}

      <div
        className="space-y-4 max-h-[400px] overflow-y-auto"
        role="list"
        aria-label="Templates list"
      >
        {Object.entries(grouped).map(([category, categoryTemplates]) => (
          <div key={category} role="group" aria-label={`${category} templates`}>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              {category}
              <span className="ml-1 text-gray-400">({categoryTemplates.length})</span>
            </h3>

            <div className="space-y-2">
              {categoryTemplates.map((template) => {
                const isExpanded = expandedTemplate === template.name;
                const catColor =
                  CATEGORY_COLORS[template.category] || CATEGORY_COLORS.general;

                return (
                  <div
                    key={template.id}
                    className="bg-gray-50 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors group"
                    role="listitem"
                  >
                    {/* ─── Card Header ─── */}
                    <div className="p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          {/* Name + Category badge */}
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-sm text-gray-900 truncate">
                              {template.name.replace(/_/g, ' ')}
                            </span>
                            <span
                              className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${catColor}`}
                            >
                              {template.category}
                            </span>
                          </div>

                          {/* Description */}
                          {template.description && (
                            <p className="text-xs text-gray-500 mb-2">
                              {template.description}
                            </p>
                          )}

                          {/* ═══ TRIGGER PHRASES (CLEARLY VISIBLE) ═══ */}
                          <div className="mt-2">
                            <div className="flex items-center gap-1 mb-1.5">
                              <Volume2 className="w-3 h-3 text-green-600" />
                              <span className="text-[10px] font-semibold text-green-700 uppercase tracking-wider">
                                Voice Triggers:
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {template.trigger_phrases.map((phrase, i) => (
                                <button
                                  key={i}
                                  onClick={() => copyTrigger(phrase)}
                                  className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-mono transition-all cursor-pointer ${
                                    copiedTrigger === phrase
                                      ? 'bg-green-200 text-green-800 border border-green-300'
                                      : 'bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 hover:border-green-300'
                                  }`}
                                  title={`Say: "insert ${phrase}" — Click to copy`}
                                >
                                  {copiedTrigger === phrase ? (
                                    <Check className="w-2.5 h-2.5" />
                                  ) : (
                                    <Mic className="w-2.5 h-2.5 opacity-60" />
                                  )}
                                  &quot;{phrase}&quot;
                                </button>
                              ))}
                            </div>
                            <p className="text-[9px] text-gray-400 mt-1 ml-0.5">
                              💡 Say <strong>&quot;insert {template.trigger_phrases[0]}&quot;</strong> while recording
                            </p>
                          </div>
                        </div>

                        {/* Action buttons */}
                        <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                          <button
                            onClick={() => handleInsert(template)}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Insert into editor"
                          >
                            <PlusCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => openEditForm(template)}
                            className="p-1.5 text-gray-500 hover:bg-gray-100 rounded transition-colors"
                            title="Edit template"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(template.name)}
                            className="p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 rounded transition-colors"
                            title="Delete template"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* ─── Preview Toggle ─── */}
                    <button
                      onClick={() =>
                        setExpandedTemplate(isExpanded ? null : template.name)
                      }
                      className="w-full flex items-center justify-center gap-1 py-1.5 text-[10px] text-gray-400 hover:bg-gray-100 transition-colors border-t border-gray-200"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="w-3 h-3" />
                          Hide Preview
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-3 h-3" />
                          Preview Content
                        </>
                      )}
                    </button>

                    {/* ─── Preview Content ─── */}
                    {isExpanded && (
                      <div className="px-3 pb-3">
                        <pre className="text-[11px] text-gray-600 bg-white p-2 rounded border border-gray-200 max-h-40 overflow-y-auto whitespace-pre-wrap font-mono leading-relaxed">
                          {template.content}
                        </pre>

                        {/* Trigger reminder in preview */}
                        <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-[10px] text-green-700">
                          <span className="font-semibold">🎤 To insert via voice, say:</span>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {template.trigger_phrases.map((phrase, i) => (
                              <code
                                key={i}
                                className="bg-green-100 px-1.5 py-0.5 rounded font-mono"
                              >
                                &quot;insert {phrase}&quot;
                              </code>
                            ))}
                          </div>
                        </div>

                        <div className="flex justify-end mt-2">
                          <button
                            onClick={() => handleInsert(template)}
                            className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                          >
                            Insert Template
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* ═════════════════════════════════════════════════════════ */}
      {/* CREATE / EDIT FORM                                       */}
      {/* ═════════════════════════════════════════════════════════ */}

      <div className="border-t border-gray-200 pt-4">
        <button
          onClick={() => (isFormOpen ? closeForm() : openCreateForm())}
          className="w-full flex items-center justify-between px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        >
          {isFormOpen
            ? editingTemplate
              ? `Editing: ${editingTemplate.name}`
              : 'New Template'
            : 'Create Template'}
          <ChevronDown
            className={`w-4 h-4 transition-transform ${isFormOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {isFormOpen && (
          <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
            {/* Name */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Template Name *
              </label>
              <input
                type="text"
                placeholder="e.g. my_custom_note"
                value={formName}
                onChange={(e) =>
                  setFormName(e.target.value.toLowerCase().replace(/\s+/g, '_'))
                }
                disabled={!!editingTemplate}
                className={`w-full px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  editingTemplate
                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                    : 'border-gray-300'
                } ${formErrors.name ? 'border-red-500' : ''}`}
              />
              {formErrors.name && (
                <p className="text-xs text-red-600 mt-1">{formErrors.name}</p>
              )}
            </div>

            {/* Trigger Phrases */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Voice Trigger Phrases *
              </label>
              <input
                type="text"
                placeholder="e.g. my note, custom note, insert my note"
                value={formTriggers}
                onChange={(e) => setFormTriggers(e.target.value)}
                className={`w-full px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  formErrors.triggers ? 'border-red-500' : 'border-gray-300'
                }`}
              />
              {formErrors.triggers && (
                <p className="text-xs text-red-600 mt-1">{formErrors.triggers}</p>
              )}
              <p className="text-[10px] text-gray-500 mt-1">
                Comma-separated. Users will say &quot;insert [phrase]&quot; to trigger.
              </p>
            </div>

            {/* Category */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {TEMPLATE_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {/* Description */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Description
              </label>
              <input
                type="text"
                placeholder="Brief description"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Author */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Author
              </label>
              <input
                type="text"
                placeholder="Your name"
                value={formAuthor}
                onChange={(e) => setFormAuthor(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Content */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Template Content *
              </label>
              <textarea
                placeholder="Enter template content... Use ___ for blanks"
                value={formContent}
                onChange={(e) => setFormContent(e.target.value)}
                className={`w-full px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none font-mono ${
                  formErrors.content ? 'border-red-500' : 'border-gray-300'
                }`}
                rows={8}
              />
              {formErrors.content && (
                <p className="text-xs text-red-600 mt-1">{formErrors.content}</p>
              )}
            </div>

            {/* Submit Error */}
            {formErrors.submit && (
              <div className="px-3 py-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                {formErrors.submit}
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="flex-1 px-3 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isSubmitting && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                {editingTemplate ? 'Update' : 'Create'}
              </button>
              <button
                onClick={closeForm}
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
