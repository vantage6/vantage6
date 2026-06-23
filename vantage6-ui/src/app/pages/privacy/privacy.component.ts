import { Component, ChangeDetectionStrategy } from '@angular/core';
import { MatCard, MatCardContent, MatCardHeader, MatCardTitle } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-privacy',
  templateUrl: './privacy.component.html',
  styleUrls: ['./privacy.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MatCard, MatCardContent, MatCardHeader, MatCardTitle, MatIcon, TranslateModule]
})
export class PrivacyComponent {}
