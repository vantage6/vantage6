import { Component, HostBinding } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { Router } from '@angular/router';
import { readFile } from 'src/app/helpers/file.helper';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { EncryptionService } from 'src/app/services/encryption.service';
import { PermissionService } from 'src/app/services/permission.service';

// import * as JSEncrypt from 'jsencrypt';

@Component({
  selector: 'app-upload-private-key',
  templateUrl: './upload-private-key.component.html',
  styleUrl: './upload-private-key.component.scss'
})
export class UploadPrivateKeyComponent {
  @HostBinding('class') class = 'card-container';

  selectedFile: File | null = null;
  uploadForm = this.fb.nonNullable.group({
    privateKeyFile: ''
  });

  constructor(
    private router: Router,
    private fb: FormBuilder,
    private permissionService: PermissionService,
    private encryptionService: EncryptionService
  ) {}

  async onFileUpload(event: Event) {
    this.selectedFile = (event.target as HTMLInputElement).files?.item(0) || null;

    if (!this.selectedFile) return;
    const fileData = await readFile(this.selectedFile);
    if (!fileData) return;

    this.encryptionService.setPrivateKey(fileData);
    if (this.permissionService.isAllowedWithMinScope(ScopeType.COLLABORATION, ResourceType.TASK, OperationType.VIEW)) {
      this.router.navigate([routePaths.tasks]);
    } else {
      this.router.navigate([routePaths.analyzeHome]);
    }
  }
}
