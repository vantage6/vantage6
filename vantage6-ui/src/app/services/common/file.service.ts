import { Injectable } from '@angular/core';
import { saveAs } from 'file-saver';

@Injectable({
  providedIn: 'root',
})
export class FileService {
  constructor() {}

  downloadTxtFile(text: string, filename: string): void {
    const blob = new Blob([text], { type: 'text/txt' });
    saveAs(blob, filename);
  }

  uploadFile($event: any): File | null {
    if ($event.target.files && $event.target.files.length > 0) {
      return $event.target.files.item(0);
    }
    return null;
  }

  readFile(file: File): Promise<string | undefined> {
    return new Promise<string | undefined>((resolve, reject) => {
      let fileReader = new FileReader();
      fileReader.onload = (e) => {
        const content = fileReader.result?.toString();
        resolve(content);
      };
      fileReader.onerror = reject;
      fileReader.readAsText(file);
    });
  }
}
