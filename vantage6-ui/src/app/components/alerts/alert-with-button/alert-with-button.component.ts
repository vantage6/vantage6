import { Component, Input } from '@angular/core';
import { MatButton } from '@angular/material/button';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'app-alert-with-button',
    templateUrl: './alert-with-button.component.html',
    styleUrls: ['./alert-with-button.component.scss'],
    imports: [MatButton, RouterLink]
})
export class AlertWithButtonComponent {
  @Input() label: string = '';
  @Input() buttonText: string = '';
  @Input() buttonLink: string = '';
  @Input() isSuccessAlert: boolean = true;

  getAlertClasses(): string {
    return this.isSuccessAlert ? `alert alert-success` : `alert`;
  }
}
