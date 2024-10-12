import { AbstractControl, FormControl, FormGroup, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { floatListRegex, floatRegex, intListRegex, integerRegex, stringListRegex } from 'src/app/helpers/regex.helper';
import { AlgorithmFunction, ArgumentType } from 'src/app/models/api/algorithm.model';
import { TaskDatabase } from 'src/app/models/api/task.models';
import { Database } from 'src/app/models/api/node.model';

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
    const requiredValidators = argument.has_default_value ? [] : [Validators.required];
    if (argument.type === ArgumentType.String || argument.type === ArgumentType.Column) {
      form.addControl(argument.name, new FormControl(null, requiredValidators));
    }
    if (argument.type === ArgumentType.Integer || argument.type === ArgumentType.Organization) {
      form.addControl(argument.name, new FormControl(null, [...requiredValidators, Validators.pattern(integerRegex)]));
    }
    if (argument.type === ArgumentType.Float) {
      form.addControl(argument.name, new FormControl(null, [...requiredValidators, Validators.pattern(floatRegex)]));
    }
    if (argument.type === ArgumentType.Json) {
      form.addControl(argument.name, new FormControl(null, [...requiredValidators, jsonValidator()]));
    }
    if (argument.type === ArgumentType.Boolean) {
      form.addControl(argument.name, new FormControl(false, requiredValidators));
    }
    if (argument.type === ArgumentType.OrganizationList || argument.type === ArgumentType.IntegerList) {
      // validate that the input is a list of integers
      form.addControl(argument.name, new FormControl(null, [...requiredValidators, Validators.pattern(intListRegex)]));
    }
    if (argument.type === ArgumentType.IntegerList) {
      // validate that the input is a list of integers
      form.addControl(argument.name, new FormControl(null, [...requiredValidators, Validators.pattern(intListRegex)]));
    }
    if (argument.type === ArgumentType.FloatList) {
      // validate that the input is a list of floats
      form.addControl(argument.name, new FormControl(null, [...requiredValidators, Validators.pattern(floatListRegex)]));
    }
    if (argument.type === ArgumentType.ColumnList) {
      // validate that the input is a list of strings
      form.addControl(argument.name, new FormControl(null, [...requiredValidators, Validators.pattern(stringListRegex)]));
    }
    if (argument.type === ArgumentType.StringList) {
      // validate that the input is a list of strings
      form.addControl(argument.name, new FormControl(null, [...requiredValidators, Validators.pattern(stringListRegex)]));
    }
    // set default value
    if (argument.has_default_value && argument.default_value) {
      form.get(argument.name)?.setValue(argument.default_value);
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
      taskDatabase.sheet_name = sheet;
    }
    taskDatabases.push(taskDatabase);
  });
  return taskDatabases;
};

export const getDatabaseTypesFromForm = (func: AlgorithmFunction | null, form: FormGroup, availableDatabases: Database[]): Database[] => {
  const databases: Database[] = [];
  func?.databases.forEach((functionDatabase) => {
    const selected_database = form.get(`${functionDatabase.name}_name`)?.value || '';
    const database = availableDatabases.find((_) => _.name === selected_database);
    if (database) {
      databases.push(database);
    }
  });
  return databases;
};
