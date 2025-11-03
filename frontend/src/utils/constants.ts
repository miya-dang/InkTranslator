import type { Language } from './types';

export const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'english', name: 'English' },
  { code: 'sim_chinese', name: 'Simplified Chinese' },
  { code: 'trad_chinese', name: 'Traditional Chinese' },
  { code: 'korean', name: 'Korean' },
  { code: 'japanese', name: 'Japanese' },
  { code: 'vietnamese', name: 'Vietnamese' },
];

export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000/api/v1',
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10 MB
  ALLOWED_TYPES: ['image/png', 'image/jpeg'] as readonly string[],
  ALLOWED_EXTENSIONS: ['.png', '.jpg', '.jpeg'] as readonly string[],
} as const;
