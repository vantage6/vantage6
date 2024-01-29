import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MfaLostComponent } from './mfa-lost.component';

describe('MfaLostComponent', () => {
  let component: MfaLostComponent;
  let fixture: ComponentFixture<MfaLostComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [MfaLostComponent]
    });
    fixture = TestBed.createComponent(MfaLostComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
