// lib/api.ts

import { API_URL } from './constants';
import type {
  Template,
  TemplateCreate,
  TemplateUpdate,
  TemplateListResponse,
  TemplateTestResponse,
} from '@/types';

// ═══════════════════════════════════════════════════════════════
// API CLIENT
// ═══════════════════════════════════════════════════════════════

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: `HTTP ${response.status}` }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      return response.json();
    } catch (error: any) {
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        throw new Error('Cannot connect to server. Is the backend running?');
      }
      throw error;
    }
  }

  // ─────────────────────────────────────────────────────────
  // HEALTH
  // ─────────────────────────────────────────────────────────

  async getHealth(): Promise<any> {
    return this.request('/health');
  }

  // ─────────────────────────────────────────────────────────
  // TEMPLATES - LIST & SEARCH
  // ─────────────────────────────────────────────────────────

  async getTemplates(
    category?: string,
    search?: string
  ): Promise<TemplateListResponse> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (search) params.append('search', search);

    const query = params.toString();
    return this.request<TemplateListResponse>(
      `/api/templates/${query ? `?${query}` : ''}`
    );
  }

  async getTemplate(name: string): Promise<Template> {
    return this.request<Template>(`/api/templates/${name}`);
  }

  async getCategories(): Promise<string[]> {
    return this.request<string[]>('/api/templates/categories');
  }

  async getTemplateStats(): Promise<any> {
    return this.request('/api/templates/stats');
  }

  async getTriggers(): Promise<any> {
    return this.request('/api/templates/triggers');
  }

  // ─────────────────────────────────────────────────────────
  // TEMPLATES - CRUD
  // ─────────────────────────────────────────────────────────

  async createTemplate(data: TemplateCreate): Promise<Template> {
    return this.request<Template>('/api/templates/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTemplate(
    name: string,
    data: TemplateUpdate
  ): Promise<Template> {
    return this.request<Template>(`/api/templates/${name}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteTemplate(
    name: string,
    hardDelete: boolean = false
  ): Promise<any> {
    return this.request(`/api/templates/${name}?hard_delete=${hardDelete}`, {
      method: 'DELETE',
    });
  }

  // ─────────────────────────────────────────────────────────
  // TEMPLATES - UTILITIES
  // ─────────────────────────────────────────────────────────

  async testTemplateProcessing(
    text: string
  ): Promise<TemplateTestResponse> {
    return this.request<TemplateTestResponse>('/api/templates/test', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }

  async refreshTemplates(): Promise<any> {
    return this.request('/api/templates/refresh', {
      method: 'POST',
    });
  }
}

// ═══════════════════════════════════════════════════════════════
// GLOBAL INSTANCE
// ═══════════════════════════════════════════════════════════════

export const api = new ApiClient(API_URL);