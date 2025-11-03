import type { SupportedLanguagesResponse, ProcessingStatusResponse } from './types';
import { API_CONFIG } from './constants';

export class ApiError extends Error {
  public status: number;
  public type: string;

  constructor(message: string, status: number = 500, type: string = 'unknown_error') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.type = type;
  }
}

export class ApiService {
  private static baseUrl = API_CONFIG.BASE_URL;

  private static async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let errorData: any;
      try {
        errorData = await response.json();
      } catch {
        errorData = {
          error: 'network_error',
          detail: `HTTP ${response.status}: ${response.statusText}`,
        };
      }

      throw new ApiError(
        errorData.detail || errorData.message || 'Request failed',
        response.status,
        errorData.error || 'http_error'
      );
    }

    const contentType = response.headers.get('content-type');

    if (contentType?.startsWith('image/')) {
      return response.blob() as Promise<T>;
    }
    if (contentType?.includes('application/json')) {
      return response.json();
    }
    return response.text() as Promise<T>;
  }

  private static createHeaders(additionalHeaders: Record<string, string> = {}): HeadersInit {
    return { ...additionalHeaders };
  }

  private static generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  static async translateImage(
    file: File,
    sourceLanguage: string,
    targetLanguage: string,
    onStatus?: (message: string) => void,
    sessionId?: string
  ): Promise<Blob> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_language', sourceLanguage);
    formData.append('target_language', targetLanguage);

    if (sessionId) {
      formData.append('session_id', sessionId);
    }

    try {
      const response = await fetch(`${this.baseUrl}/translate`, {
        method: 'POST',
        body: formData,
        headers: this.createHeaders(),
      });

      // Start polling for step messages
      if (sessionId && onStatus) {
        this.pollTranslationStatus(sessionId, onStatus);
      }

      return this.handleResponse<Blob>(response);
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(
        error instanceof Error ? error.message : 'Translation request failed',
        0,
        'network_error'
      );
    }
  }

  static async getSupportedLanguages(): Promise<SupportedLanguagesResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/supported-languages`, {
        method: 'GET',
        headers: this.createHeaders(),
      });

      return this.handleResponse<SupportedLanguagesResponse>(response);
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError('Failed to fetch supported languages', 0, 'network_error');
    }
  }

  static async getStatus(sessionId: string): Promise<ProcessingStatusResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/status/${sessionId}`, {
        method: 'GET',
        headers: this.createHeaders(),
      });

      return this.handleResponse<ProcessingStatusResponse>(response);
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError('Failed to fetch processing status', 0, 'network_error');
    }
  }

  private static async pollTranslationStatus(
    sessionId: string,
    onStatus: (message: string) => void,
    maxAttempts: number = 30,
    interval: number = 1000
  ): Promise<void> {
    let attempts = 0;

    const poll = async () => {
      try {
        attempts++;
        const status = await this.getStatus(sessionId);

        if (status?.message) {
          onStatus(status.message); // ✅ emit step message
        }

        if (status?.status !== 'COMPLETED' && status?.status !== 'ERROR' && attempts < maxAttempts) {
          setTimeout(poll, interval);
        }
      } catch (error) {
        console.warn('Status polling failed:', error);
      }
    };

    setTimeout(poll, 500);
  }

  static async healthCheck(): Promise<{ status: string; service: string; version: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        headers: this.createHeaders(),
      });

      return this.handleResponse<{ status: string; service: string; version: string }>(response);
    } catch {
      throw new ApiError('Health check failed', 0, 'network_error');
    }
  }

  static async batchTranslateImages(
    files: File[],
    sourceLanguage: string,
    targetLanguage: string,
    onStatus?: (message: string) => void,
    sessionId?: string
  ): Promise<Blob> {
    if (files.length > 3) {
      throw new ApiError('Maximum 3 files allowed per batch', 400, 'validation_error');
    }

    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('source_language', sourceLanguage);
    formData.append('target_language', targetLanguage);

    if (sessionId) {
      formData.append('session_id', sessionId);
    }

    try {
      const response = await fetch(`${this.baseUrl}/batch-translate`, {
        method: 'POST',
        body: formData,
        headers: this.createHeaders(),
      });

      if (sessionId && onStatus) {
        this.pollTranslationStatus(sessionId, onStatus);
      }

      return this.handleResponse<Blob>(response);
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError('Batch translation failed', 0, 'network_error');
    }
  }

  static createSession(): string {
    return this.generateSessionId();
  }

  static async cancelTranslation(sessionId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/cancel/${sessionId}`, {
        method: 'POST',
        headers: this.createHeaders(),
      });
      await this.handleResponse<void>(response);
    } catch (error) {
      console.warn('Failed to cancel translation:', error);
    }
  }
}

export const useApi = () => {
  return {
    translateImage: ApiService.translateImage,
    getSupportedLanguages: ApiService.getSupportedLanguages,
    getStatus: ApiService.getStatus,
    healthCheck: ApiService.healthCheck,
    batchTranslateImages: ApiService.batchTranslateImages,
    createSession: ApiService.createSession,
    cancelTranslation: ApiService.cancelTranslation,
  };
};

export type {
  Language,
  TranslationRequest,
  ApiErrorInterface,
  SupportedLanguagesResponse,
  ProcessingStage,
  ProcessingStatusResponse,
} from './types';
