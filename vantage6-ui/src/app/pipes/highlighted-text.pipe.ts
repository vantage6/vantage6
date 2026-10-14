/* eslint-disable @typescript-eslint/no-explicit-any */
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'highlight',
  standalone: true
})
export class HighlightedTextPipe implements PipeTransform {
  transform(value: any, args: any, enabled: boolean): unknown {
    if (typeof value !== 'string') return value;

    const escapeHtml = (text: string) =>
      text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    if (!args || !enabled) return escapeHtml(value);

    const search = String(args).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(search, 'gi');
    let result = '';
    let lastIndex = 0;
    for (const match of value.matchAll(re)) {
      result += escapeHtml(value.slice(lastIndex, match.index));
      result += `<strong>${escapeHtml(match[0])}</strong>`;
      lastIndex = match.index + match[0].length;
    }
    return result + escapeHtml(value.slice(lastIndex));
  }
}
