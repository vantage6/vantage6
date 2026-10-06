export const integerRegex: string = '^-{0,1}[0-9]*$';
export const floatRegex: string = '^-{0,1}[0-9]*[,.]?[0-9]*$';
export const intListRegex: string = '^\\d+(,\\d+)*$';
export const floatListRegex: string = '^\\d+(\\.\\d+)?(,\\d+(\\.\\d+)?)*$';
export const stringListRegex: string = '^[\\w]+(,[\\w]+)*$';

/*
 * Pattern that matches the given base URLs and any of their subpaths.
 */
export function getUrlPattern(urls: string[]): RegExp {
  const escapedUrls = urls.map((url) => {
    const escaped = url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return `${escaped}(/.*)?`;
  });
  return new RegExp(`^(${escapedUrls.join('|')})$`, 'i');
}
