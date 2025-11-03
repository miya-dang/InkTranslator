// components/OptionsPanel.tsx
import React from 'react';
import { SUPPORTED_LANGUAGES } from '../utils/constants';

interface OptionsPanelProps {
  sourceLanguage: string;
  targetLanguage: string;
  onSourceLanguageChange: (language: string) => void;
  onTargetLanguageChange: (language: string) => void;
  disabled?: boolean;
}

const OptionsPanel: React.FC<OptionsPanelProps> = ({
  sourceLanguage,
  targetLanguage,
  onSourceLanguageChange,
  onTargetLanguageChange,
  disabled = false
}) => (
  <div className="mt-4 p-4 border rounded shadow">
    <h3 className="text-lg font-semibold mb-2">Translation Options</h3>
    
    <label className="block mb-2 text-sm">
      Source Language:
      <select 
        className="ml-2 border p-1 rounded disabled:bg-gray-100"
        value={sourceLanguage}
        onChange={(e) => onSourceLanguageChange(e.target.value)}
        disabled={disabled}
      >
        {SUPPORTED_LANGUAGES.map(lang => (
          <option key={lang.code} value={lang.code}>
            {lang.name}
          </option>
        ))}
      </select>
    </label>
    
    <label className="block mb-2 text-sm">
      Target Language:
      <select 
        className="ml-2 border p-1 rounded disabled:bg-gray-100"
        value={targetLanguage}
        onChange={(e) => onTargetLanguageChange(e.target.value)}
        disabled={disabled}
      >
        {SUPPORTED_LANGUAGES.map(lang => (
          <option key={lang.code} value={lang.code}>
            {lang.name}
          </option>
        ))}
      </select>
    </label>
  </div>
);

export default OptionsPanel;
