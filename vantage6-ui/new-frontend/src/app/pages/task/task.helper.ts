import { FormControl, FormGroup, Validators } from '@angular/forms';
import { floatRegex, integerRegex } from 'src/app/helpers/regex.helper';
import { AlgorithmFunction, ArgumentType } from 'src/app/models/api/algorithm.model';

export const addParameterFormControlsForFunction = (func: AlgorithmFunction, form: FormGroup) => {
  func?.arguments.forEach((argument) => {
    if (argument.type === ArgumentType.String) {
      form.addControl(argument.name, new FormControl(null, Validators.required));
    }
    if (argument.type === ArgumentType.Integer) {
      form.addControl(argument.name, new FormControl(null, [Validators.required, Validators.pattern(integerRegex)]));
    }
    if (argument.type === ArgumentType.Float) {
      form.addControl(argument.name, new FormControl(null, [Validators.required, Validators.pattern(floatRegex)]));
    }
  });
};
