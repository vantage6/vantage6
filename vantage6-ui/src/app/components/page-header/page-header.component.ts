import { Component, Input } from '@angular/core';
import { MatCard, MatCardContent } from '@angular/material/card';

@Component({
    selector: 'app-page-header',
    templateUrl: './page-header.component.html',
    styleUrls: ['./page-header.component.scss'],
    imports: [MatCard, MatCardContent]
})
export class PageHeaderComponent {
  @Input() title: string = '';
}
