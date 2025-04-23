import { Component, Input, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatChipGrid, MatChipInput, MatChipInputEvent, MatChipRow, MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule, MatLabel } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-mat-chip-form',
  templateUrl: './mat-chip-form.component.html',
  styleUrls: ['./mat-chip-form.component.scss'],
  imports: [MatIconModule, MatChipsModule, MatFormFieldModule, MatLabel, MatChipRow, MatChipGrid, MatChipInput, ReactiveFormsModule]
})
export class MatChipFormComponent {
  @Input() initialValues!: string[];
  @Input() formcontrol!: FormControl<unknown>;
  @Input() placeholder = 'placeholder';
  @Input() label = 'label';

  readonly values = signal(this.initialValues);

  ngOnInit() {
    this.values.set(this.initialValues);
  }

  removeTemplateKeyword(keyword: string) {
    this.values.update((keywords) => {
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
      this.values.update((keywords) => [...keywords, value]);
    }

    event.chipInput!.clear();
  }
}
