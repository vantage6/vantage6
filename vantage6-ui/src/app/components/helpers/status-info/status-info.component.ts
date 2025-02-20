import { Component, Input } from '@angular/core';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { NgClass, NgIf } from '@angular/common';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { MatIcon } from '@angular/material/icon';

@Component({
  selector: 'app-status-info',
  templateUrl: './status-info.component.html',
  styleUrls: ['./status-info.component.scss'],
  standalone: true,
  imports: [NgClass, NgIf, MatProgressSpinner, MatIcon, TranslateModule]
})
export class StatusInfoComponent {
  @Input() taskName: string = '';
  @Input() nodeName: string = '';
  @Input() status: string = '';
  @Input() type: 'pending' | 'active' | 'success' | 'error' = 'pending';

  constructor(public translateService: TranslateService) {}

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
