import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { CHOSEN_COLLAB_PRIVATE_KEY } from '../models/constants/sessionStorage';
import JSEncrypt from 'jsencrypt';
import { Buffer } from 'buffer';
import * as crypto from 'crypto';
import * as CryptoJS from 'crypto-js';
import * as NodeRSA from 'node-rsa';
import { OrganizationService } from './organization.service';

@Injectable({
  providedIn: 'root'
})
export class DecryptionService {
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

  async encryptData(data: string = 'test'): Promise<string> {
    const SEPARATOR = '$';
    const organizationId = 1;

    const organization = await this.organizationService.getOrganization(organizationId.toString());
    if (!organization) {
      return data;
    }
    const pubKey = organization.public_key;
    const pubKeyDecoded = atob(pubKey);

    // TODO use these random keys later - for now fixed for testing
    // const iv = CryptoJS.lib.WordArray.random(16);
    // const sharedKey = CryptoJS.lib.WordArray.random(32);

    const sharedKeyBytes = [
      141, 81, 85, 156, 198, 163, 208, 195, 106, 38, 64, 253, 146, 76, 166, 154, 140, 247, 121, 187, 98, 68, 56, 24, 126, 151, 154, 130,
      250, 129, 82, 67
    ];
    const ivBytes = [47, 80, 108, 139, 64, 98, 121, 99, 69, 230, 7, 11, 61, 106, 97, 104];
    const iv = this.bytestowordarray(ivBytes);
    const sharedKey = this.bytestowordarray(sharedKeyBytes);
    // const sharedKey

    // const sharedKeyTest = CryptoJS.lib.WordArray.random(32);
    // console.log(sharedKeyTest);
    // const sharedKey = CryptoJS.lib.WordArray.create(sharedKeyBytes);
    const sharedKeyPlainText = 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb';
    // const sharedKey = CryptoJS.enc.Hex.parse(sharedKeyPlainText);
    // console.log(sharedKey);
    // console.log(sharedKey.toString());
    // console.log('sharedkey', sharedKey);

    // const iv = CryptoJS.lib.WordArray.random(16);
    // const iv2 = CryptoJS.lib.WordArray.create(ivBytes, 16);
    // console.log('iv', iv2);
    // console.log(this.wordarraytobytes(iv2));
    // const iv = CryptoJS.enc.Hex.parse('3e23e8160039594a33894f6564e1b134');
    console.log('iv', iv);
    console.log(this.wordarraytobytes(iv));

    // console.log(this.wordarraytobytes(sharedKey));

    //         cipher = Cipher(
    //   algorithms.AES(shared_key), modes.CTR(iv_bytes), backend=default_backend()
    // )
    // encryptor = cipher.encryptor()
    // encrypted_msg_bytes = encryptor.update(data) + encryptor.finalize()

    // Encrypt the data synchronously. This is done syncronously because asynchronous
    // encryption is slow and produces bigger encrypted data.
    const syncEncryptor = CryptoJS.algo.AES.createEncryptor(sharedKey, {
      mode: CryptoJS.mode.CTR,
      iv: iv,
      padding: CryptoJS.pad.NoPadding
    });
    syncEncryptor.process(data);
    const encryptedMsgBytes = syncEncryptor.finalize();
    // console.log(encryptedMsgBytes);
    // console.log(this.wordarraytobytes(encryptedMsgBytes));
    const encryptedMsg = CryptoJS.enc.Base64.stringify(encryptedMsgBytes);
    console.log(encryptedMsg);

    // # Create a public key instance.
    // pubkey = load_pem_public_key(
    //     base64s_to_bytes(pubkey_base64s), backend=default_backend()
    // )
    // encrypted_key_bytes = pubkey.encrypt(shared_key, padding.PKCS1v15())

    // encrypt the shared key asynchronously (i.e. using the public key)
    const asyncEncryptor = new JSEncrypt();
    asyncEncryptor.setPublicKey(pubKeyDecoded);
    // console.log('pub key length', pubKeyDecoded.length);
    console.log(sharedKey);
    console.log(sharedKey.toString(CryptoJS.enc.Base64));
    console.log(sharedKey.toString());
    const encryptedKey = asyncEncryptor.encrypt(sharedKey.toString(CryptoJS.enc.Base64));
    if (!encryptedKey) {
      throw new Error('Failed to encrypt shared key using public key.');
    }
    console.log(encryptedKey);
    console.log('length', encryptedKey.length);
    const blub = Buffer.from(encryptedKey, 'base64');
    console.log(blub);
    const blubber = blub.toString('base64');
    console.log(blubber);
    console.log('length', blubber.length);
    // // decrypt the shared key using the private key
    // if (!this.privateKey$.value) {
    //   throw new Error('No private key set.');
    // }
    // const decrypt = new JSEncrypt();
    // decrypt.setPrivateKey(this.privateKey$.value);
    // const decryptedKey = decrypt.decrypt(encryptedKey);
    // console.log(decryptedKey);

    // encrypted_key = self.bytes_to_str(encrypted_key_bytes)
    // iv = self.bytes_to_str(iv_bytes)
    // encrypted_msg = self.bytes_to_str(encrypted_msg_bytes)

    // return SEPARATOR.join([encrypted_key, iv, encrypted_msg])
    const encryptedKeyB64 = this.bytesToBase64(Buffer.from(encryptedKey));
    const ivB64 = this.bytesToBase64(this.wordarraytobytes(iv));

    // console.log(encryptedKeyB64);
    // console.log('');
    // console.log('');
    // console.log('');
    // console.log(ivB64);
    // console.log(encryptedMsg);
    // console.log('');
    // console.log(encryptedKeyB64 + SEPARATOR + ivB64 + SEPARATOR + encryptedMsg);
    return encryptedKeyB64 + SEPARATOR + ivB64 + SEPARATOR + encryptedMsg;
  }

  private bytesToBase64(bytes: Uint8Array): string {
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private wordarraytobytes(wordArray: CryptoJS.lib.WordArray): Uint8Array {
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
