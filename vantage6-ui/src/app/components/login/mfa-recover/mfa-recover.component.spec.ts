import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MfaRecoverComponent } from './mfa-recover.component';

describe('MfaRecoverComponent', () => {
  let component: MfaRecoverComponent;
  let fixture: ComponentFixture<MfaRecoverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MfaRecoverComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MfaRecoverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
