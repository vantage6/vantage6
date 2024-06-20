import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StoreUserEditComponent } from './store-user-edit.component';

describe('StoreUserEditComponent', () => {
  let component: StoreUserEditComponent;
  let fixture: ComponentFixture<StoreUserEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [StoreUserEditComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(StoreUserEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
