import { LANGUAGES, useI18n } from '../i18n.js';

export default function LanguageSelector({ compact = false }) {
  const { language, setLanguage, t } = useI18n();
  return (
    <label className={compact ? 'language-select compact' : 'language-select'}>
      {!compact && <span>{t('language')}</span>}
      <select value={language} onChange={(e) => setLanguage(e.target.value)}>
        {LANGUAGES.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
      </select>
    </label>
  );
}
