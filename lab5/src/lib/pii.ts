// PII patterns to scrub before API call and before log write
// Production upgrade path: Presidio sidecar for ML-based detection
// Current approach: regex, covers the high-risk categories

const PII_PATTERNS: { name: string; pattern: RegExp }[] = [
    {
      name: 'email',
      pattern: /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g,
    },
    {
      name: 'phone',
      // Covers: (555) 123-4567, 555-123-4567, 555.123.4567, +1 555 123 4567
      pattern: /(\+?1?\s?)(\(?\d{3}\)?[\s.\-]?)(\d{3}[\s.\-]\d{4})/g,
    },
    {
      name: 'ssn',
      pattern: /\b\d{3}-\d{2}-\d{4}\b/g,
    },
    {
      name: 'credit_card',
      // Covers 13-19 digit card numbers with optional spaces/dashes
      pattern: /\b(?:\d[ \-]?){13,19}\b/g,
    },
    {
      name: 'ip_address',
      pattern: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g,
    },
  ];
  
  export function scrubPII(text: string): string {
    let scrubbed = text;
    for (const { name, pattern } of PII_PATTERNS) {
      scrubbed = scrubbed.replace(pattern, `[REDACTED_${name.toUpperCase()}]`);
    }
    return scrubbed;
  }
  
  export function containsPII(text: string): boolean {
    return PII_PATTERNS.some(({ pattern }) => {
      pattern.lastIndex = 0; // reset stateful regex
      return pattern.test(text);
    });
  }