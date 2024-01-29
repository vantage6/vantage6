import { Injectable } from '@angular/core';
import { saveAs } from 'file-saver';

@Injectable({
  providedIn: 'root'
})
export class FileService {
  constructor() {}

  downloadTxtFile(text: string, filename: string): void {
    const blob = new Blob([text], { type: 'text/txt' });
    saveAs(blob, filename);
  }
}
