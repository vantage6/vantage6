import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { CHOSEN_COLLAB_PRIVATE_KEY } from '../models/constants/sessionStorage';
import { Buffer } from 'buffer';
import * as CryptoJS from 'crypto-js';
import forge from 'node-forge';
import { OrganizationService } from './organization.service';
import { ENCRYPTION_SEPARATOR } from '../models/constants/encryption';

@Injectable({
  providedIn: 'root'
})
export class EncryptionService {
  privateKey$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  constructor(private organizationService: OrganizationService) {
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
    const encryptedKey = splittedData[0];
    const iv = splittedData[1];
    const encrypted_msg = splittedData[2];
    // console.log(encryptedKey);

    // to bytes array
    // const encrypted_key_bytes = atob(encrypted_key);
    // const iv_bytes = atob(iv);
    // const encrypted_msg_bytes = atob(encrypted_msg);
    const encrypted_key_bytes = Buffer.from(encryptedKey, 'base64');
    const iv_bytes = Buffer.from(iv, 'base64');
    const encrypted_msg_bytes = Buffer.from(encrypted_msg, 'base64');
    // console.log(encrypted_key_bytes);
    // console.log(iv_bytes);
    // console.log(encrypted_msg_bytes);
    // console.log(Buffer.from(encrypted_key_bytes, 'utf8'));
    // console.log(Buffer.from(encrypted_key, 'utf8'));

    // --------------------------------------------
    // -----  FYI python reproduced until here ----
    // --------------------------------------------

    // // // decrypt shared key using assymetric encryption
    // // const decrypt = new JSEncrypt();
    // // decrypt.setPrivateKey(this.privateKey$.value);
    // // const sharedKey = decrypt.decrypt(encrypted_key_bytes);
    // // console.log(sharedKey);
    // // decrypt shared key using assymetric encryption
    // const key = CryptoJS.lib.WordArray.create(encrypted_key_bytes);
    // const keyb64 = CryptoJS.enc.Base64.stringify(key);
    // const ivKey = CryptoJS.lib.WordArray.create(iv_bytes);
    // const tryKey = CryptoJS.enc.Base64.stringify(CryptoJS.enc.Base64.parse(encryptedKey));
    // console.log(encryptedKey);
    // console.log(tryKey);
    // // CryptoJS.enc.Hex.parse(encryptedKey);

    // // Reproduce Python code below
    // // shared_key = self.private_key.decrypt(encrypted_key_bytes, padding.PKCS1v15())
    // try {
    //   console.log(keyb64);
    //   const sharedKey = CryptoJS.AES.decrypt(encryptedKey, this.privateKey$.value);
    //   // const sharedKey = CryptoJS.AES.decrypt(encryptedKey, this.privateKey$.value, { iv: ivKey });
    //   console.log(sharedKey);
    //   console.log(sharedKey.toString());
    //   const sharedKeyHex = CryptoJS.enc.Hex.stringify(sharedKey);
    //   const sharedKeyBytes = [];
    //   for (let i = 0; i < sharedKeyHex.length; i += 2) {
    //     sharedKeyBytes.push(parseInt(sharedKeyHex.substr(i, 2), 16));
    //   }
    //   console.log(sharedKeyBytes);
    // } catch (error) {
    //   console.log(error);
    // }
    // const decrypt = new JSEncrypt();
    // decrypt.setPrivateKey(this.privateKey$.value);
    // const sharedKey = decrypt.decrypt(encrypted_key_bytes.toString());
    // console.log(sharedKey);

    // TODO reproduce Python code below
    // # Use the shared key for symmetric encryption/decryption of the payload
    // cipher = Cipher(
    //     algorithms.AES(shared_key), modes.CTR(iv_bytes), backend=default_backend()
    // )
    // const cipher = CryptoJS.AES.encrypt(encrypted_msg, sharedKey.toString());

    // TODO reproduce Python code below
    // decryptor = cipher.decryptor()
    // result = decryptor.update(encrypted_msg_bytes) + decryptor.finalize()

    // const key = crypto.privateDecrypt(this.privateKey$.value, encrypted_key_bytes);
    // console.log(key);

    // Use the shared key for symmetric encryption/decryption of the payload
    // const decipher = crypto.createDecipheriv('aes-256-ctr', Buffer.from(sharedKey, 'hex'), iv_bytes);
    // let decrypted = decipher.update(encrypted_msg_bytes);
    // console.log(decrypted);
    // decrypted = Buffer.concat([decrypted, decipher.finalize()]);

    // const cipher = crypto.createCipher('aes-128-ecb', key);
    // console.log(cipher);
    // let tokenHex = cipher.update('HELLO\x00\x00', 'utf8', 'hex');
    // tokenHex = tokenHex.toString('utf8')

    // return decrypt.decrypt(encryptedData) || encryptedData;
    return encryptedData;
  }

  async encryptData(data: string, organizationID: number): Promise<string> {
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

    // convert the encrypted message to base64 string
    const encryptedMsgB64 = CryptoJS.enc.Base64.stringify(encryptedMsgBytes);

    // encrypt the shared key asynchronously (i.e. using the public key)
    const publicKey = forge.pki.publicKeyFromPem(pubKeyDecoded);
    const encryptedKey = publicKey.encrypt(sharedKey.toString(CryptoJS.enc.Base64), 'RSAES-PKCS1-V1_5');

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

  private bytestowordarray(bytes: number[]): CryptoJS.lib.WordArray {
    // const ivWords = [];
    // for (let i = 0; i < ivBytes.length; i += 4) {
    //   ivWords.push((ivBytes[i] << 24) | (ivBytes[i + 1] << 16) | (ivBytes[i + 2] << 8) | ivBytes[i + 3]);
    // }
    // const iv2 = CryptoJS.lib.WordArray.create(ivWords);
    const words = [];
    for (let i = 0; i < bytes.length; i += 4) {
      const word = (bytes[i] << 24) | (bytes[i + 1] << 16) | (bytes[i + 2] << 8) | bytes[i + 3];
      words.push(word);
    }
    return CryptoJS.lib.WordArray.create(words, bytes.length);
  }
}
