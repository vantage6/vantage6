import { Validators } from '@angular/forms';

export const PASSWORD_VALIDATORS = [
  Validators.minLength(8),
  Validators.pattern(/(?=.*[A-Z])/),
  Validators.pattern(/(?=.*[a-z])/),
  Validators.pattern(/(?=.*\d)/),
  Validators.pattern(/(?=.*\W)/)
];
