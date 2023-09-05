import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-status-info',
  templateUrl: './status-info.component.html',
  styleUrls: ['./status-info.component.scss']
})
export class StatusInfoComponent {
  @Input() title: string = '';
  @Input() subTitle: string = '';
  @Input() type: 'pending' | 'active' | 'success' | 'error' = 'pending';

  getClasses(): string {
    return `status-info--${this.type}`;
  }

  getIcon(): string {
    switch (this.type) {
      case 'error':
        return 'error';
      case 'success':
        return 'check_circle';
      default:
        return '';
    }
  }

  get shouldShowLoader(): boolean {
    return this.type === 'pending' || this.type === 'active';
  }
}
