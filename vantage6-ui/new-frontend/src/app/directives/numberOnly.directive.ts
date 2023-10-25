//Directive to allow only numbers (int and float) in a number input field

import { Directive, HostListener } from '@angular/core';

@Directive({
  selector: '[numberOnly]'
})
export class NumberOnlyDirective {
  @HostListener('keydown', ['$event'])
  onKeyDown(event: KeyboardEvent) {
    if (event.target && (event.target as HTMLInputElement).type !== 'number') {
      return true; // Check if input is of type number
    }
    console.log(event.key);
    if (event.key === '' || event.key.length > 1) {
      return true; // Allow space, backspace, tab, enter, arrows, etc
    }
    return !!event.key.match(/[0-9,.-]/); // Only allow numbers, comma and dot
  }
}
