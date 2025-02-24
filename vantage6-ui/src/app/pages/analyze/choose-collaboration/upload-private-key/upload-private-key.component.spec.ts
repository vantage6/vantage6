import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UploadPrivateKeyComponent } from './upload-private-key.component';

describe('UploadPrivateKeyComponent', () => {
  let component: UploadPrivateKeyComponent;
  let fixture: ComponentFixture<UploadPrivateKeyComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadPrivateKeyComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(UploadPrivateKeyComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
