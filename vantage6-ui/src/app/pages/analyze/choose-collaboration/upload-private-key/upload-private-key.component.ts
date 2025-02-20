import { Component, HostBinding } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { readFile } from 'src/app/helpers/file.helper';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { EncryptionService } from 'src/app/services/encryption.service';
import { PermissionService } from 'src/app/services/permission.service';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatFormField, MatLabel, MatSuffix } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatButton } from '@angular/material/button';
import { TranslateModule } from '@ngx-translate/core';

// import * as JSEncrypt from 'jsencrypt';

@Component({
  selector: 'app-upload-private-key',
  templateUrl: './upload-private-key.component.html',
  styleUrl: './upload-private-key.component.scss',
  standalone: true,
  imports: [
    PageHeaderComponent,
    MatCard,
    MatCardContent,
    ReactiveFormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatButton,
    MatSuffix,
    TranslateModule
  ]
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
