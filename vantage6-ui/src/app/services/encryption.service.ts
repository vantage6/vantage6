import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { CHOSEN_COLLAB_PRIVATE_KEY } from '../models/constants/sessionStorage';
import { Buffer } from 'buffer';
import * as CryptoJS from 'crypto-js';
import forge from 'node-forge';
import { OrganizationService } from './organization.service';
import { ENCRYPTION_SEPARATOR } from '../models/constants/encryption';
import { ChosenCollaborationService } from './chosen-collaboration.service';

@Injectable({
  providedIn: 'root'
})
export class EncryptionService {
  privateKey$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  constructor(
    private organizationService: OrganizationService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {
    this.initData();
  }

  async setPrivateKey(privateKey: string) {
    this.privateKey$.next(privateKey);
    sessionStorage.setItem(CHOSEN_COLLAB_PRIVATE_KEY, privateKey);
  }

  clear() {
    this.privateKey$.next(null);
    sessionStorage.removeItem(CHOSEN_COLLAB_PRIVATE_KEY);
  }

  private async initData() {
    const privateKey = sessionStorage.getItem(CHOSEN_COLLAB_PRIVATE_KEY);
    if (privateKey) {
      this.privateKey$.next(privateKey);
    }
  }

  decryptData(encryptedData: string): string {
    if (!this.privateKey$.value || this.chosenCollaborationService.isEncrypted() === false) {
      return encryptedData;
    }

    // split the encrypted data
    const splittedData = encryptedData.split('$');
    const encryptedSharedKey = splittedData[0];
    const encryptedIV = splittedData[1];
    const encryptedMsg = splittedData[2];

    // to bytes array
    const encryptedSharedKeyBytes = Buffer.from(encryptedSharedKey, 'base64');
    const encryptedIVBytes = Buffer.from(encryptedIV, 'base64');

    // decrypt shared key using assymetric encryption
    const privateKey = forge.pki.privateKeyFromPem(this.privateKey$.value);
    const decryptedSharedKey = privateKey.decrypt(encryptedSharedKeyBytes.toString('binary'), 'RSAES-PKCS1-V1_5');
    let decryptedSharedKeyBytes;
    try {
      // shared key has additional layer of base64 encoding if it was encoded by the UI
      decryptedSharedKeyBytes = Buffer.from(atob(decryptedSharedKey), 'binary');
    } catch (error) {
      // if that didn't work, it was encrypted by Python - no additional layer of base64 encoding
      decryptedSharedKeyBytes = Buffer.from(decryptedSharedKey, 'binary');
    }

    // convert shared key and IV to WordArray
    const decryptedSharedKeyWordArray = this.bufferToWordArray(decryptedSharedKeyBytes);
    const ivWordArray = this.bufferToWordArray(encryptedIVBytes);

    // decrypt message with symmetric encryption using the shared key
    const decipher = CryptoJS.AES.decrypt(encryptedMsg, decryptedSharedKeyWordArray, {
      iv: ivWordArray,
      mode: CryptoJS.mode.CTR,
      padding: CryptoJS.pad.NoPadding
    });

    // convert the decrypted message to string
    const decryptedMsg = decipher.toString(CryptoJS.enc.Utf8);

    // if the decrypted message was encrypted by the UI, there is an additional layer
    // of base64 encoding that needs to be removed
    try {
      return atob(decryptedMsg);
    } catch (error) {
      return decryptedMsg;
    }
  }

  async encryptData(data: string, organizationID: number): Promise<string> {
    // if collaboration is not encrypted, return the data as is
    if (this.chosenCollaborationService.isEncrypted() === false) {
      return data;
    }

    // get the public key of the organization
    const organization = await this.organizationService.getOrganization(organizationID.toString());
    if (!organization) {
      return data;
    }
    const pubKey = organization.public_key;
    const pubKeyDecoded = atob(pubKey);

    // Define the shared key and iv
    const sharedKey = CryptoJS.lib.WordArray.random(32);
    const iv = CryptoJS.lib.WordArray.random(16);

    // Encrypt the data synchronously using the shared key. This is done syncronously
    // because asynchronous encryption is slower and produces bigger encrypted data.
    const syncEncryptor = CryptoJS.algo.AES.createEncryptor(sharedKey, {
      mode: CryptoJS.mode.CTR,
      iv: iv,
      padding: CryptoJS.pad.NoPadding
    });
    const firstEncryptedPart = syncEncryptor.process(data);
    const secondEncryptedPart = syncEncryptor.finalize();
    const encryptedMsgBytes = firstEncryptedPart.concat(secondEncryptedPart);

    // convert the encrypted message and key to base64 string
    const encryptedMsgB64 = CryptoJS.enc.Base64.stringify(encryptedMsgBytes);
    const sharedKeyB64 = sharedKey.toString(CryptoJS.enc.Base64);

    // encrypt the shared key asynchronously (i.e. using the public key)
    const publicKey = forge.pki.publicKeyFromPem(pubKeyDecoded);
    const encryptedKey = publicKey.encrypt(sharedKeyB64, 'RSAES-PKCS1-V1_5');

    // convert the encrypted key and iv to base64 string
    const encryptedKeyB64 = btoa(encryptedKey);
    const ivB64 = this.bytesToBase64(this.wordArrayToBytes(iv));

    return encryptedKeyB64 + ENCRYPTION_SEPARATOR + ivB64 + ENCRYPTION_SEPARATOR + encryptedMsgB64;
  }

  private bytesToBase64(bytes: Uint8Array): string {
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private wordArrayToBytes(wordArray: CryptoJS.lib.WordArray): Uint8Array {
    const words = wordArray.words;
    const sigBytes = wordArray.sigBytes;
    const bytes = [];
    for (let i = 0; i < sigBytes; i++) {
      const byte = (words[i >>> 2] >>> (24 - (i % 4) * 8)) & 0xff;
      bytes.push(byte);
    }
    return new Uint8Array(bytes);
  }

  private bufferToWordArray(buffer: Buffer): CryptoJS.lib.WordArray {
    const words = [];
    for (let i = 0; i < buffer.length; i += 4) {
      const word = (buffer[i] << 24) | (buffer[i + 1] << 16) | (buffer[i + 2] << 8) | buffer[i + 3];
      words.push(word);
    }
    return CryptoJS.lib.WordArray.create(words, buffer.length);
  }
}
