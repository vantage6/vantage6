import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SetupMfaComponent } from './setup-mfa.component';

describe('SetupMfaComponent', () => {
  let component: SetupMfaComponent;
  let fixture: ComponentFixture<SetupMfaComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [SetupMfaComponent]
    });
    fixture = TestBed.createComponent(SetupMfaComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
