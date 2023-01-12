export function removeArrayDoubles(array: any[]): any[] {
  return [...new Set(array)];
}

export function deepcopy(obj: any): any {
  return JSON.parse(JSON.stringify(obj));
  // return Object.assign({}, obj);
}

export function removeMatchedIdFromArray(array: any[], id: number): any[] {
  // remove the elements from an array that have a certain id
  return array.filter(function (elem: any) {
    return elem.id !== id;
  });
}

export function removeMatchedIdsFromArray(array: any[], ids: number[]): any[] {
  // remove the elements from an array that have some id values
  for (let id of ids) {
    array = removeMatchedIdFromArray(array, id);
  }
  return array;
}

export function removeDuplicateIds(array: any[]): any[] {
  // remove duplicate id elements
  return array.filter(
    (value, index, self) =>
      index === self.findIndex((value2) => value2.id === value.id)
  );
}

export function filterByOtherArrayIds(
  big_array: any[],
  small_array: any[]
): any[] {
  // return all objects in big array with ids that do NOT occur in the small array
  return big_array.filter((big) => {
    return small_array.every((small) => {
      return small.id !== big.id;
    });
  });
}

export function filterArray(array: any[], to_remove: any[]): any[] {
  return array.filter((el) => !to_remove.includes(el));
}

export function filterArrayByProperty(
  arr: any[],
  property: string,
  value: any,
  has_property: boolean = true
) {
  return has_property
    ? arr.filter((el) => el[property] === value)
    : arr.filter((el) => el[property] !== value);
}

export function removeValueFromArray(array: any[], value: any): any[] {
  return array.filter((el) => el !== value);
}

export function getById(array: any[], id: number): any | undefined {
  return array.find((x) => x.id === id);
}

export function getIdsFromArray(
  array: any[],
  id_field: string = 'id'
): number[] {
  return array.map((a) => {
    return a[id_field];
  });
}

export function replaceMatchedId(array: any[], replacer: any) {
  return array.map((original) =>
    original.id === replacer.id ? replacer : original
  );
}

export function addOrReplace(array: any[], new_val: any) {
  if (getById(array, new_val.id)) {
    return replaceMatchedId(array, new_val);
  } else {
    array.push(new_val);
    return array;
  }
}

export function arrayContainsObjWithId(id: number, array: any[]) {
  return array.some((u) => u.id === id);
}

export function containsObject(obj: any, list: any[]) {
  // check if list of objects contains a specific object
  for (let i = 0; i < list.length; i++) {
    if (list[i] === obj) {
      return true;
    }
  }
  return false;
}

export function arrayContains(array: any[], value: any) {
  return array.includes(value);
}

export function isSubset(small_array: any[], large_array: any[]) {
  return small_array.every((val) => large_array.includes(val));
}

export function parseId(id: string | null): number {
  if (id === null) {
    id = '';
  }
  return parseInt(id);
}

export function arrayIdsEqual(arr1: any[], arr2: any[]): boolean {
  if (arr1.length !== arr2.length) return false;
  for (let i = 0; i < arr1.length; i++) {
    if (arr1[i].id !== arr2[i].id) return false;
  }
  return true;
}

export function unique(array: any[]): any[] {
  return array.filter((val, idx, arr) => arr.indexOf(val) === idx);
}

export function getUniquePropertyValues(array: any[], property: any): any[] {
  // return all unique values of a specific property
  return [
    ...new Set(
      array.map((item) => {
        return item[property];
      })
    ),
  ];
}

export function enumIncludes(an_enum: any, value: any): boolean {
  return Object.values(an_enum).includes(value);
}

export function dictEmpty(dict: any): boolean {
  return dict && Object.keys(dict).length === 0;
}
