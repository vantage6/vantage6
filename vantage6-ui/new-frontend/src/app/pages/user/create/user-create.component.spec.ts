import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserCreateComponent } from './user-create.component';

describe('UserCreateComponent', () => {
  let component: UserCreateComponent;
  let fixture: ComponentFixture<UserCreateComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [UserCreateComponent]
    });
    fixture = TestBed.createComponent(UserCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
