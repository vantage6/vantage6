import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlertWithButtonComponent } from './alert-with-button.component';

describe('AlertWithButtonComponent', () => {
  let component: AlertWithButtonComponent;
  let fixture: ComponentFixture<AlertWithButtonComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [AlertWithButtonComponent]
    });
    fixture = TestBed.createComponent(AlertWithButtonComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
