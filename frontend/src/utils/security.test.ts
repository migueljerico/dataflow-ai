
import { describe, it, expect, beforeEach } from 'vitest';
import { saveApiKey, getApiKey, removeApiKey } from './security';

describe('security vault', () => {
  beforeEach(() => localStorage.clear());
  it('round-trips key via vault', () => { saveApiKey('AIzaSy-test'); expect(getApiKey()).toBe('AIzaSy-test'); });
  it('remove clears both keys', () => { saveApiKey('k'); removeApiKey(); expect(getApiKey()).toBeNull(); });
  it('migrates legacy key', () => { localStorage.setItem('dataflow_gemini_api_key','legacy123'); expect(getApiKey()).toBe('legacy123'); });
});
