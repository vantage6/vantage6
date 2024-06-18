import { Component, HostBinding } from '@angular/core';
import { routePaths } from 'src/app/routes';

@Component({
  selector: 'app-base-create',
  templateUrl: './base-create.component.html',
  styleUrl: './base-create.component.scss'
})
export class BaseCreateComponent {
  @HostBinding('class') class = 'card-container';
  routes = routePaths;

  isSubmitting: boolean = false;
}
