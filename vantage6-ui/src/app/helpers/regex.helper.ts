export const integerRegex: string = '^-{0,1}[0-9]*$';
export const floatRegex: string = '^-{0,1}[0-9]*[,.]?[0-9]*$';
export const intListRegex: string = '^\\d+(,\\d+)*$';
export const floatListRegex: string = '^\\d+(\\.\\d+)?(,\\d+(\\.\\d+)?)*$';
export const stringListRegex: string = '^[\\w]+(,[\\w]+)*$';

/*
 * Create a pattern that tells whether a request URL is one of the given base URLs
 * or a path below one of them (case insensitive). For example, for
 * ['https://hq.example.org/api'] it matches 'https://hq.example.org/api' and
 * 'https://hq.example.org/api/task/1', but not 'https://hq.example.org/apifoo' or
 * 'https://evil.org/?https://hq.example.org/api'.
 */
export function getUrlPattern(urls: string[]): RegExp {
  const escapedUrls = urls.map((url) => {
    // escape characters that have a special meaning in regular expressions, such as
    // '.', so that they only match themselves
    const escaped = url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    // optionally followed by a slash and any subpath
    return `${escaped}(/.*)?`;
  });
  // the full URL must match one of the base URLs (with optional subpath)
  return new RegExp(`^(${escapedUrls.join('|')})$`, 'i');
}
