import { scrubPII, containsPII } from './pii';

describe('scrubPII', () => {
  // Email
  it('redacts email addresses', () => {
    const result = scrubPII('Contact me at dave@example.com for details');
    expect(result).not.toMatch(/dave@example\.com/);
    expect(result).toContain('[REDACTED_EMAIL]');
  });

  // Phone
  it('redacts US phone numbers', () => {
    const result = scrubPII('Call me at (555) 123-4567');
    expect(result).not.toMatch(/555.*123.*4567/);
    expect(result).toContain('[REDACTED_PHONE]');
  });

  it('redacts dashed phone format', () => {
    const result = scrubPII('My number is 555-123-4567');
    expect(result).not.toMatch(/555-123-4567/);
  });

  // SSN
  it('redacts SSNs', () => {
    const result = scrubPII('My SSN is 123-45-6789');
    expect(result).not.toMatch(/123-45-6789/);
    expect(result).toContain('[REDACTED_SSN]');
  });

  // Credit card
  it('redacts credit card numbers', () => {
    const result = scrubPII('Card number 4111 1111 1111 1111 expires soon');
    expect(result).not.toMatch(/4111/);
    expect(result).toContain('[REDACTED_CREDIT_CARD]');
  });

  // IP address
  it('redacts IP addresses', () => {
    const result = scrubPII('Server at 192.168.1.1 is down');
    expect(result).not.toMatch(/192\.168\.1\.1/);
    expect(result).toContain('[REDACTED_IP_ADDRESS]');
  });

  // Multiple PII types in one string
  it('redacts multiple PII types in a single message', () => {
    const result = scrubPII(
      'Email dave@example.com or call 555-123-4567, SSN 123-45-6789'
    );
    expect(result).not.toMatch(/dave@example\.com/);
    expect(result).not.toMatch(/555-123-4567/);
    expect(result).not.toMatch(/123-45-6789/);
  });

  // Clean text passes through unchanged
  it('leaves clean text unmodified', () => {
    const clean = 'Please help me write a cover letter for a software job';
    expect(scrubPII(clean)).toBe(clean);
  });
});

describe('containsPII', () => {
  it('returns true when PII is present', () => {
    expect(containsPII('My email is test@example.com')).toBe(true);
  });

  it('returns false when no PII present', () => {
    expect(containsPII('The weather today is sunny')).toBe(false);
  });
});