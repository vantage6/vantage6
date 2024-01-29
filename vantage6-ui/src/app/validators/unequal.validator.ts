import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export function createUnEqualValidator(controlName: string, compareControlName: string): ValidatorFn {
  return (form: AbstractControl): ValidationErrors | null => {
    const control = form.get(controlName);
    const compareControl = form.get(compareControlName);
    if (control?.value && compareControl?.value) {
      const isUnequal = control.value !== compareControl.value;
      if (!isUnequal) {
        control.setErrors({ ...control.errors, compare: true });
        compareControl.setErrors({ ...control.errors, compare: true });
      } else {
        const newControlErrors = { ...control.errors };
        if (newControlErrors['compare']) {
          delete newControlErrors['compare'];
        }
        control.setErrors(Object.keys(newControlErrors).length ? newControlErrors : null);
        const newCompareControlErrors = { ...compareControl.errors };
        if (newCompareControlErrors['compare']) {
          delete newCompareControlErrors['compare'];
        }
        compareControl.setErrors(Object.keys(newCompareControlErrors).length ? newCompareControlErrors : null);
      }
      return !isUnequal ? { unequal: true } : null;
    }

    return null;
  };
}
