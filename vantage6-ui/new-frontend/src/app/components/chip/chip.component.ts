import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-chip',
  templateUrl: './chip.component.html',
  styleUrls: ['./chip.component.scss']
})
export class ChipComponent {
  @Input() label: string = '';
  @Input() type: 'default' | 'active' | 'success' | 'warning' | 'error' = 'default';
  @Input() small: boolean = false;
  @Input() clickable: boolean = false;

  getTypeClass(): string {
    const classNames: string[] = [];
    if (this.type !== 'default') {
      classNames.push(`chip--${this.type}`);
    }
    if (this.small) {
      classNames.push('chip--small');
    }
    if (this.clickable) {
      classNames.push('chip--clickable');
    }
    return classNames.join(' ');
  }
}
