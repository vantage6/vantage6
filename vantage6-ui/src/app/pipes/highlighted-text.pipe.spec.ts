import { HighlightedTextPipe } from './highlighted-text.pipe';

describe('HighlightedTextPipe', () => {
  const pipe = new HighlightedTextPipe();

  it('highlights search terms with regex metacharacters literally', () => {
    expect(pipe.transform('Total (net) [EUR]', '(net)', true)).toBe('Total <strong>(net)</strong> [EUR]');
    expect(pipe.transform('Total [net]', '[net]', true)).toBe('Total <strong>[net]</strong>');
  });

  it('escapes label markup while retaining only generated highlighting tags', () => {
    expect(pipe.transform('<img src=x onerror=alert(1)> & value', 'value', true)).toBe(
      '&lt;img src=x onerror=alert(1)&gt; &amp; <strong>value</strong>'
    );
  });

  it('escapes labels even when highlighting is disabled', () => {
    expect(pipe.transform('<em>label</em>', '', false)).toBe('&lt;em&gt;label&lt;/em&gt;');
  });

  it('escapes matched HTML instead of introducing label markup', () => {
    expect(pipe.transform('<em>label</em>', '<em>', true)).toBe('<strong>&lt;em&gt;</strong>label&lt;/em&gt;');
  });

  it('highlights literal replacement tokens without changing matched text', () => {
    expect(pipe.transform('cost $&', '$&', true)).toBe('cost <strong>$&amp;</strong>');
  });
});
