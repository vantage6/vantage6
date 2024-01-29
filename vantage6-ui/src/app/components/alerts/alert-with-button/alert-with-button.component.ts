import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-alert-with-button',
  templateUrl: './alert-with-button.component.html',
  styleUrls: ['./alert-with-button.component.scss']
})
export class AlertWithButtonComponent {
  @Input() label: string = '';
  @Input() buttonText: string = '';
  @Input() buttonLink: string = '';
}
