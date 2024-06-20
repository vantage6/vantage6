import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StoreUserFormComponent } from './store-user-form.component';

describe('StoreUserFormComponent', () => {
  let component: StoreUserFormComponent;
  let fixture: ComponentFixture<StoreUserFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [StoreUserFormComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(StoreUserFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
