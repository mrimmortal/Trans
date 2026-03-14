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
  Eye,
  EyeOff,
  AlertCircle,
  FileText,
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

  // Form fields
  const [formName, setFormName] = useState('');
  const [formTriggers, setFormTriggers] = useState('');
  const [formContent, setFormContent] = useState('');
  const [formCategory, setFormCategory] = useState('custom');
  const [formDescription, setFormDescription] = useState('');
  const [formAuthor, setFormAuthor] = useState('');
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // ─────────────────────────────────────────────────────────
  // FORM RESET
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
  // SUBMIT HANDLER
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
        // Update existing template
        await updateTemplate(editingTemplate.name, {
          trigger_phrases: triggerPhrases,
          content: formContent,
          category: formCategory,
          description: formDescription,
          author: formAuthor,
        });
        onToast?.('Template updated successfully', 'success');
      } else {
        // Create new template
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
  // DELETE HANDLER
  // ─────────────────────────────────────────────────────────

  const handleDelete = async (name: string) => {
    if (!window.confirm(`Delete template "${name}"? This can be undone later.`)) {
      return;
    }

    try {
      await deleteTemplate(name);
      onToast?.('Template deleted', 'success');
    } catch (err: any) {
      onToast?.(err.message || 'Failed to delete template', 'error');
    }
  };

  // ─────────────────────────────────────────────────────────
  // INSERT HANDLER
  // ─────────────────────────────────────────────────────────

  const handleInsert = (template: Template) => {
    onInsertTemplate(template.content);
    onToast?.(`Inserted "${template.name.replace(/_/g, ' ')}" template`, 'command');
  };

  // ─────────────────────────────────────────────────────────
  // GROUP TEMPLATES BY CATEGORY
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
    <div className="flex flex-col gap-4">
      {/* ─── SEARCH & ACTIONS ─── */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search templates..."
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

      {/* ─── CATEGORY FILTER ─── */}
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
            All
          </button>
          {categories.map((cat) => (
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
              {cat}
            </button>
          ))}
        </div>
      )}

      {/* ─── ERROR DISPLAY ─── */}
      {error && (
        <div className="flex items-start gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-xs text-red-700">{error}</p>
          </div>
          <button
            onClick={clearError}
            className="text-red-400 hover:text-red-600"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ─── LOADING STATE ─── */}
      {isLoading && templates.length === 0 && (
        <div className="flex items-center justify-center py-8">
          <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* ─── TEMPLATES LIST ─── */}
      {!isLoading && templates.length === 0 && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <FileText className="w-10 h-10 text-gray-300 mb-2" />
          <p className="text-sm text-gray-500">No templates found</p>
          <p className="text-xs text-gray-400 mt-1">
            Create one or check your backend connection
          </p>
        </div>
      )}

      <div
        className="space-y-4 max-h-96 overflow-y-auto"
        role="list"
        aria-label="Templates list"
      >
        {Object.entries(grouped).map(([category, categoryTemplates]) => (
          <div key={category} role="group" aria-label={`${category} templates`}>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              {category}
              <span className="ml-1 text-gray-400">
                ({categoryTemplates.length})
              </span>
            </h3>
            <div className="space-y-2">
              {categoryTemplates.map((template) => {
                const isExpanded = expandedTemplate === template.name;
                const catColor =
                  CATEGORY_COLORS[template.category] ||
                  CATEGORY_COLORS.general;

                return (
                  <div
                    key={template.id}
                    className="bg-gray-50 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors group"
                    role="listitem"
                  >
                    {/* Template Header */}
                    <div className="p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
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

                          {template.description && (
                            <p className="text-xs text-gray-500 line-clamp-1">
                              {template.description}
                            </p>
                          )}

                          {/* Trigger phrases */}
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {template.trigger_phrases
                              .slice(0, 2)
                              .map((phrase, i) => (
                                <span
                                  key={i}
                                  className="px-1.5 py-0.5 text-[10px] bg-gray-100 text-gray-600 rounded font-mono"
                                >
                                  &ldquo;{phrase}&rdquo;
                                </span>
                              ))}
                            {template.trigger_phrases.length > 2 && (
                              <span className="text-[10px] text-gray-400">
                                +{template.trigger_phrases.length - 2} more
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Action buttons */}
                        <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
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

                    {/* Expand/Collapse Preview */}
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
                          Preview
                        </>
                      )}
                    </button>

                    {/* Preview Content */}
                    {isExpanded && (
                      <div className="px-3 pb-3">
                        <pre className="text-[11px] text-gray-600 bg-white p-2 rounded border border-gray-200 max-h-40 overflow-y-auto whitespace-pre-wrap font-mono leading-relaxed">
                          {template.content}
                        </pre>
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

      {/* ═══════════════════════════════════════════════════════ */}
      {/* CREATE / EDIT FORM                                     */}
      {/* ═══════════════════════════════════════════════════════ */}

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
              {!editingTemplate && (
                <p className="text-[10px] text-gray-500 mt-1">
                  Lowercase letters, numbers, underscores only
                </p>
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
                <p className="text-xs text-red-600 mt-1">
                  {formErrors.triggers}
                </p>
              )}
              <p className="text-[10px] text-gray-500 mt-1">
                Comma-separated. Say &ldquo;insert [phrase]&rdquo; while dictating.
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
                placeholder="Brief description of this template"
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
                placeholder="Enter your template content here..."
                value={formContent}
                onChange={(e) => setFormContent(e.target.value)}
                className={`w-full px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none font-mono ${
                  formErrors.content ? 'border-red-500' : 'border-gray-300'
                }`}
                rows={8}
              />
              {formErrors.content && (
                <p className="text-xs text-red-600 mt-1">
                  {formErrors.content}
                </p>
              )}
              <p className="text-[10px] text-gray-500 mt-1">
                Use ___ for blanks to fill in later
              </p>
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
                className="flex-1 px-3 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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