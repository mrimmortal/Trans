// hooks/useTemplates.ts
'use client';

import { useState, useCallback, useEffect } from 'react';
import { api } from '@/lib/api';
import type { Template, TemplateCreate, TemplateUpdate } from '@/types';

export interface UseTemplatesReturn {
  templates: Template[];
  categories: string[];
  isLoading: boolean;
  error: string | null;
  selectedCategory: string | null;
  searchQuery: string;
  setSelectedCategory: (category: string | null) => void;
  setSearchQuery: (query: string) => void;
  fetchTemplates: () => Promise<void>;
  createTemplate: (data: TemplateCreate) => Promise<Template>;
  updateTemplate: (name: string, data: TemplateUpdate) => Promise<Template>;
  deleteTemplate: (name: string) => Promise<void>;
  refreshTemplates: () => Promise<void>;
  clearError: () => void;
}

export function useTemplates(): UseTemplatesReturn {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [initialized, setInitialized] = useState(false);

  // Fetch templates from backend
  const fetchTemplates = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.getTemplates(
        selectedCategory || undefined,
        searchQuery || undefined
      );
      setTemplates(response.templates);
      setCategories(response.categories);
    } catch (err: any) {
      const message = err.message || 'Failed to fetch templates';
      setError(message);
      console.error('Error fetching templates:', err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, searchQuery]);

  // Create template
  const createTemplate = useCallback(
    async (data: TemplateCreate): Promise<Template> => {
      try {
        setError(null);
        const template = await api.createTemplate(data);
        // Refresh list after creation
        await fetchTemplates();
        return template;
      } catch (err: any) {
        const message = err.message || 'Failed to create template';
        setError(message);
        throw new Error(message);
      }
    },
    [fetchTemplates]
  );

  // Update template
  const updateTemplate = useCallback(
    async (name: string, data: TemplateUpdate): Promise<Template> => {
      try {
        setError(null);
        const template = await api.updateTemplate(name, data);
        await fetchTemplates();
        return template;
      } catch (err: any) {
        const message = err.message || 'Failed to update template';
        setError(message);
        throw new Error(message);
      }
    },
    [fetchTemplates]
  );

  // Delete template
  const deleteTemplate = useCallback(
    async (name: string): Promise<void> => {
      try {
        setError(null);
        await api.deleteTemplate(name);
        await fetchTemplates();
      } catch (err: any) {
        const message = err.message || 'Failed to delete template';
        setError(message);
        throw new Error(message);
      }
    },
    [fetchTemplates]
  );

  // Refresh templates (reload from backend + re-register commands)
  const refreshTemplates = useCallback(async () => {
    try {
      setError(null);
      await api.refreshTemplates();
      await fetchTemplates();
    } catch (err: any) {
      const message = err.message || 'Failed to refresh templates';
      setError(message);
      throw new Error(message);
    }
  }, [fetchTemplates]);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Initial fetch
  useEffect(() => {
    if (!initialized) {
      setInitialized(true);
      fetchTemplates();
    }
  }, [initialized, fetchTemplates]);

  // Refetch when category or search changes
  useEffect(() => {
    if (initialized) {
      fetchTemplates();
    }
  }, [selectedCategory, searchQuery]);

  return {
    templates,
    categories,
    isLoading,
    error,
    selectedCategory,
    searchQuery,
    setSelectedCategory,
    setSearchQuery,
    fetchTemplates,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    refreshTemplates,
    clearError,
  };
}