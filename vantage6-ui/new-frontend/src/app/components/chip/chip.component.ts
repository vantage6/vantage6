import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-chip',
  templateUrl: './chip.component.html',
  styleUrls: ['./chip.component.scss']
})
export class ChipComponent {
  @Input() label: string = '';
  @Input() type: 'default' | 'active' | 'success' | 'warning' | 'error' = 'default';

  getTypeClass(): string {
    if (this.type === 'default') {
      return '';
    } else {
      return `chip--${this.type}`;
    }
  }
}
