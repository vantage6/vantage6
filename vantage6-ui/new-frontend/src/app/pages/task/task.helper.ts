import { AbstractControl, FormControl, FormGroup, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { floatRegex, integerRegex } from 'src/app/helpers/regex.helper';
import { AlgorithmFunction, ArgumentType } from 'src/app/models/api/algorithm.model';
import { TaskDatabase } from 'src/app/models/api/task.models';

function jsonValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const error: ValidationErrors = { jsonInvalid: true };

    try {
      JSON.parse(control.value);
    } catch (e) {
      control.setErrors(error);
      return error;
    }

    control.setErrors(null);
    return null;
  };
}

export const addParameterFormControlsForFunction = (func: AlgorithmFunction, form: FormGroup) => {
  func?.arguments.forEach((argument) => {
    if (argument.type === ArgumentType.String || argument.type === ArgumentType.Column) {
      form.addControl(argument.name, new FormControl(null, Validators.required));
    }
    if (argument.type === ArgumentType.Integer) {
      form.addControl(argument.name, new FormControl(null, [Validators.required, Validators.pattern(integerRegex)]));
    }
    if (argument.type === ArgumentType.Float) {
      form.addControl(argument.name, new FormControl(null, [Validators.required, Validators.pattern(floatRegex)]));
    }
    if (argument.type === ArgumentType.Json) {
      form.addControl(argument.name, new FormControl(null, [Validators.required, jsonValidator()]));
    }
  });
};

export const getTaskDatabaseFromForm = (func: AlgorithmFunction | null, form: FormGroup): TaskDatabase[] => {
  const taskDatabases: TaskDatabase[] = [];
  func?.databases.forEach((functionDatabase) => {
    const selected_database = form.get(`${functionDatabase.name}_name`)?.value || '';
    const taskDatabase: TaskDatabase = { label: selected_database };
    const query = form.get(`${functionDatabase.name}_query`)?.value || '';
    if (query) {
      taskDatabase.query = query;
    }
    const sheet = form.get(`${functionDatabase.name}_sheet`)?.value || '';
    if (sheet) {
      taskDatabase.sheet = sheet;
    }
    taskDatabases.push(taskDatabase);
  });
  return taskDatabases;
};
