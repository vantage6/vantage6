/* eslint-disable @typescript-eslint/no-explicit-any */
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'highlight',
  standalone: true
})
export class HighlightedTextPipe implements PipeTransform {
  transform(value: any, args: any, enabled: boolean): unknown {
    if (!args || !enabled) return value;
    const re = new RegExp('(?![^<]*>)' + args, 'igm');
    value = value.replace(re, '<strong>$&</strong>');
    return value;
  }
}
