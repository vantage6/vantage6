import { Component } from '@angular/core';
import { MatCard, MatCardContent, MatCardHeader, MatCardTitle } from '@angular/material/card';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-privacy',
  templateUrl: './privacy.component.html',
  styleUrls: ['./privacy.component.scss'],
  imports: [MatCard, MatCardContent, MatCardHeader, MatCardTitle, TranslateModule]
})
export class PrivacyComponent {
  // Component logic can be added here if needed
}
