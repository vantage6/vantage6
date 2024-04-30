import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { CHOSEN_COLLAB_PRIVATE_KEY } from '../models/constants/sessionStorage';
import JSEncrypt from 'jsencrypt';

@Injectable({
  providedIn: 'root'
})
export class DecryptionService {
  privateKey$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  constructor() {
    this.initData();
  }

  async setPrivateKey(privateKey: string) {
    this.privateKey$.next(privateKey);
    sessionStorage.setItem(CHOSEN_COLLAB_PRIVATE_KEY, privateKey);
  }

  private async initData() {
    const privateKey = sessionStorage.getItem(CHOSEN_COLLAB_PRIVATE_KEY);
    if (privateKey) {
      this.privateKey$.next(privateKey);
    }
  }

  decryptData(encryptedData: string): string {
    if (!this.privateKey$.value) return encryptedData;

    // split the encrypted data
    const splittedData = encryptedData.split('$');
    const encrypted_key = splittedData[0];
    const iv = splittedData[1];
    const encrypted_msg = splittedData[2];
    console.log(encrypted_key);
    console.log(iv);
    console.log(encrypted_msg);

    // to bytes array
    const encrypted_key_bytes = atob(encrypted_key);
    const iv_bytes = atob(iv);
    const encrypted_msg_bytes = atob(encrypted_msg);
    console.log(encrypted_key_bytes, iv_bytes, encrypted_msg_bytes);

    // decrypt shared key using assymetric encryption
    const decrypt = new JSEncrypt();
    decrypt.setPrivateKey(this.privateKey$.value);
    const sharedKey = decrypt.decrypt(encrypted_key_bytes);
    console.log(sharedKey);
    return decrypt.decrypt(encryptedData) || encryptedData;
  }
}
