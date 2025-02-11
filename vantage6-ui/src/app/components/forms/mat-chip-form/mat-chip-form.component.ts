import { Component, Input, signal } from '@angular/core';
import { FormControl } from '@angular/forms';
import { MatChipInputEvent } from '@angular/material/chips';

@Component({
  selector: 'app-mat-chip-form',
  templateUrl: './mat-chip-form.component.html',
  styleUrl: './mat-chip-form.component.scss'
})
export class MatChipFormComponent {
  @Input() initalValues!: string[];
  @Input() formcontrol!: FormControl<any>;
  @Input() placeholder = 'placeholder';
  @Input() label = 'label';

  readonly values = signal(this.initalValues);

  ngOnInit() {
    this.values.set(this.initalValues);
  }

  removeTemplateKeyword(keyword: string) {
    this.values.update(keywords => {
      const index = keywords.indexOf(keyword);
      if (index < 0) {
        return keywords;
      }

      keywords.splice(index, 1);
      return [...keywords];
    });
  }

  addTemplateKeyword(event: MatChipInputEvent): void {
    const value = (event.value || '').trim();

    if (value) {
      this.values.update(keywords => [...keywords, value]);
    }

    event.chipInput!.clear();
  }
}
