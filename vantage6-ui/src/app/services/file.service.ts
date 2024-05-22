import { Injectable } from '@angular/core';
import { saveAs } from 'file-saver';

@Injectable({
  providedIn: 'root'
})
export class FileService {
  downloadTxtFile(text: string, filename: string): void {
    const blob = new Blob([text], { type: 'text/txt' });
    saveAs(blob, filename);
  }

  downloadCsvFile(data: string, filename: string): void {
    const blob = new Blob([data], { type: 'text/csv' });
    saveAs(blob, filename);
  }
}
